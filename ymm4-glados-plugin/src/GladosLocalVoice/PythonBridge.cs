using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Text.Json;

namespace GladosLocalVoice;

internal sealed record BridgeConfig(string PythonExe, string AppDirectory, string Device = "auto", int TimeoutSeconds = 180);

internal static class PythonBridge
{
    static readonly SemaphoreSlim Gate = new(1, 1);
    static readonly ConcurrentQueue<string> Errors = new();
    static Process? worker;
    static BridgeConfig? workerConfig;
    static readonly JsonSerializerOptions JsonOptions = new() { PropertyNameCaseInsensitive = true };
    internal static int? WorkerProcessId => worker is { HasExited: false } ? worker.Id : null;

    static PythonBridge() => AppDomain.CurrentDomain.ProcessExit += (_, _) => Stop();

    static BridgeConfig LoadConfig()
    {
        var folder = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location)!;
        var path = Path.Combine(folder, "glados-config.json");
        if (!File.Exists(path))
            throw new InvalidOperationException($"GLaDOS設定がありません: {path}");
        var config = JsonSerializer.Deserialize<BridgeConfig>(File.ReadAllText(path), JsonOptions)
            ?? throw new InvalidOperationException("GLaDOS設定JSONが不正です。");
        if (!Path.IsPathFullyQualified(config.PythonExe) || !File.Exists(config.PythonExe))
            throw new InvalidOperationException("glados-config.jsonのPythonExeにPython実行ファイルの絶対パスを指定してください。");
        if (!Path.IsPathFullyQualified(config.AppDirectory) ||
            !File.Exists(Path.Combine(config.AppDirectory, "glados_local", "ymm_worker.py")))
            throw new InvalidOperationException("AppDirectoryにGLaDOS Localアプリのフォルダーを指定してください。");
        if (config.Device is not ("auto" or "cpu" or "cuda") || config.TimeoutSeconds is < 10 or > 1800)
            throw new InvalidOperationException("DeviceまたはTimeoutSecondsの設定が不正です。");
        return config;
    }

    static void EnsureWorker(BridgeConfig config)
    {
        if (worker is { HasExited: false } && workerConfig == config)
            return;
        Stop();
        while (Errors.TryDequeue(out _)) { }
        var info = new ProcessStartInfo(config.PythonExe)
        {
            WorkingDirectory = config.AppDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardInputEncoding = new UTF8Encoding(false),
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
        };
        info.ArgumentList.Add("-u");
        info.ArgumentList.Add("-m");
        info.ArgumentList.Add("glados_local.ymm_worker");
        info.Environment["PYTHONUTF8"] = "1";
        info.Environment["HF_HUB_OFFLINE"] = "1";
        info.Environment["GRADIO_ANALYTICS_ENABLED"] = "False";
        var process = new Process { StartInfo = info };
        process.ErrorDataReceived += (sender, e) =>
        {
            if (e.Data is null) return;
            Errors.Enqueue(e.Data.Length <= 2048 ? e.Data : e.Data[..2048]);
            while (Errors.Count > 16) Errors.TryDequeue(out _);
        };
        if (!process.Start()) throw new InvalidOperationException("Pythonを起動できませんでした。");
        process.BeginErrorReadLine();
        worker = process;
        workerConfig = config;
    }

    public static async Task SynthesizeAsync(string text, string language, string output, GladosParameter parameter)
    {
        await Gate.WaitAsync();
        try
        {
            var config = LoadConfig();
            EnsureWorker(config);
            var id = Guid.NewGuid().ToString("N");
            var request = new
            {
                id, command = "synthesize", text, language,
                reading_format = language == "ja" ? "ymm_yukkuri_lite" : "text",
                output = Path.GetFullPath(output), device = config.Device,
                speed = parameter.Speed,
                effects = new { pitch = parameter.Pitch, formant = parameter.Formant,
                                intonation = parameter.Intonation, gain = parameter.Gain },
            };
            await worker!.StandardInput.WriteLineAsync(JsonSerializer.Serialize(request));
            await worker.StandardInput.FlushAsync();
            var line = await worker.StandardOutput.ReadLineAsync().WaitAsync(TimeSpan.FromSeconds(config.TimeoutSeconds));
            if (line is null)
                throw new InvalidOperationException("Pythonが終了しました。" + Environment.NewLine + string.Join(Environment.NewLine, Errors));
            using var response = JsonDocument.Parse(line);
            if (response.RootElement.GetProperty("id").GetString() != id)
                throw new InvalidOperationException("Pythonとの通信応答が一致しません。");
            if (!response.RootElement.GetProperty("ok").GetBoolean())
                throw new InvalidOperationException("GLaDOS音声生成エラー: " + response.RootElement.GetProperty("error").GetString());
            if (!File.Exists(output) || new FileInfo(output).Length < 44)
                throw new InvalidOperationException("Pythonから有効なWAVファイルが返されませんでした。");
        }
        catch
        {
            // Timeout/EOF/error must never leave a stale response for the next request.
            Stop();
            throw;
        }
        finally { Gate.Release(); }
    }

    static void Stop()
    {
        var process = worker;
        worker = null;
        workerConfig = null;
        if (process is null) return;
        try { if (!process.HasExited) process.Kill(entireProcessTree: true); }
        catch (InvalidOperationException) { }
        catch (System.ComponentModel.Win32Exception) { }
        finally { process.Dispose(); }
    }
}
