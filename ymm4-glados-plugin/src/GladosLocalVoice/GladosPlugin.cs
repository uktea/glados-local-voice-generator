using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using YukkuriMovieMaker.Controls;
using YukkuriMovieMaker.Plugin.Voice;

namespace GladosLocalVoice;

public sealed class GladosPlugin : IVoicePlugin
{
    public string Name => "GLaDOS Local Voice";
    public IEnumerable<IVoiceSpeaker> Voices => new IVoiceSpeaker[] { new GladosSpeaker("en"), new GladosSpeaker("ja") };
    public bool CanUpdateVoices => false;
    public bool IsVoicesCached => true;
    public Task UpdateVoicesAsync() => Task.CompletedTask;
}

public sealed class GladosParameter : VoiceParameterBase
{
    double speed = 1.0, pitch = 0, formant = 0, intonation = 1, gain = 0;

    [Display(Name = "話速", Description = "モデルの発話速度。1.0が等速です。")]
    [TextBoxSlider("F2", "倍", 0.5, 2.0, Delay = -1)]
    [Range(0.5, 2.0), DefaultValue(1.0)]
    public double Speed { get => speed; set => Set(ref speed, value); }

    [Display(Name = "ピッチ", Description = "WORLDによるピッチ変更（半音）")]
    [TextBoxSlider("F2", "半音", -12.0, 12.0, Delay = -1)]
    [Range(-12.0, 12.0), DefaultValue(0.0)]
    public double Pitch { get => pitch; set => Set(ref pitch, value); }

    [Display(Name = "包絡移動", Description = "スペクトル包絡を移動する近似加工（半音相当）")]
    [TextBoxSlider("F2", "", -6.0, 6.0, Delay = -1)]
    [Range(-6.0, 6.0), DefaultValue(0.0)]
    public double Formant { get => formant; set => Set(ref formant, value); }

    [Display(Name = "抑揚", Description = "0で平坦、1で原音の抑揚を維持します。")]
    [TextBoxSlider("F2", "", 0.0, 2.0, Delay = -1)]
    [Range(0.0, 2.0), DefaultValue(1.0)]
    public double Intonation { get => intonation; set => Set(ref intonation, value); }

    [Display(Name = "ゲイン", Description = "音量（dB）。ピーク制限により増幅量が抑えられる場合があります。")]
    [TextBoxSlider("F1", "dB", -24.0, 12.0, Delay = -1)]
    [Range(-24.0, 12.0), DefaultValue(0.0)]
    public double Gain { get => gain; set => Set(ref gain, value); }
}

public sealed class GladosSpeaker(string language) : IVoiceSpeaker
{
    public string EngineName => "GLaDOS Local";
    public string SpeakerName => language == "ja" ? "GLaDOS 日本語近似（試作）" : "GLaDOS English";
    public string API => "GladosLocalVoice.Stdio.v1";
    public string ID => language;
    public bool IsVoiceDataCachingRequired => true;
    public SupportedTextFormat Format => language == "ja" ? SupportedTextFormat.YukkuriLite : SupportedTextFormat.English;
    public IVoiceLicense? License => null;
    public IVoiceResource? Resource => null;
    public bool IsMatch(string api, string id) => api == API && id == ID;
    public IVoiceParameter CreateVoiceParameter() => new GladosParameter();
    public IVoiceParameter MigrateParameter(IVoiceParameter currentParameter) => currentParameter is GladosParameter ? currentParameter : CreateVoiceParameter();
    public Task<string> ConvertKanjiToYomiAsync(string text, IVoiceParameter voiceParameter) => Task.FromResult(text);

    public async Task<IVoicePronounce?> CreateVoiceAsync(string text, IVoicePronounce? pronounce, IVoiceParameter? parameter, string filePath)
    {
        var p = parameter as GladosParameter ?? new GladosParameter();
        await PythonBridge.SynthesizeAsync(text, language, filePath, p);
        return null;
    }
}
