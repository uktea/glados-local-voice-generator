using System.Reflection;
using System.Runtime.Loader;
using System.Text.Json;
using System.IO;

if (args.Length < 2) throw new ArgumentException("usage: inspect|synthesize YMM4-folder [output-folder]");
var ymm = Path.GetFullPath(args[1]);
AssemblyLoadContext.Default.Resolving += (_, name) =>
{
    var file = Path.Combine(ymm, name.Name+".dll");
    return File.Exists(file) ? AssemblyLoadContext.Default.LoadFromAssemblyPath(file) : null;
};
if (args[0] == "inspect") Inspect();
else await Synthesize();

void Inspect()
{
    foreach (var dll in new[] { "YukkuriMovieMaker.Plugin.dll", "YukkuriMovieMaker.dll" })
    {
        var assembly = Assembly.LoadFrom(Path.Combine(ymm,dll));
        Type[] types;
        try { types = assembly.GetExportedTypes(); }
        catch (ReflectionTypeLoadException e) { types=e.Types.OfType<Type>().ToArray(); }
        foreach (var type in types.Where(t => t.Name.Contains("SupportedTextFormat") || t.Name.Contains("Yomi") || t.Name.Contains("Kanji") || t.Name.Contains("Pronounce") || t.Name.Contains("TextConverter")))
        {
            Console.WriteLine(type.FullName);
            if (type.IsEnum) Console.WriteLine(string.Join(", ",Enum.GetNames(type)));
            else foreach (var method in type.GetMethods(BindingFlags.Public|BindingFlags.Static|BindingFlags.Instance|BindingFlags.DeclaredOnly)) Console.WriteLine("  "+method);
        }
    }
}

async Task Synthesize()
{
    var folder = Path.GetFullPath(args[2]);
    Directory.CreateDirectory(folder);
    var plugin = new GladosLocalVoice.GladosPlugin();
    var voices=plugin.Voices.ToArray();
    if(voices.Length!=2) throw new Exception("Unexpected voices");
    foreach(var voice in voices)
    {
        // Japanese speakers receive the host's kana reading, not the caption text.
        var text=voice.ID=="en"?"Hello, test subject.":"/げんざいの/せっていを/ふまえて、/ちょうせいばんを/せいせいしました。";
        var path=Path.Combine(folder,voice.ID+" test.wav");
        await voice.CreateVoiceAsync(text,null,voice.CreateVoiceParameter(),path);
        if(new FileInfo(path).Length<1000) throw new Exception("No audio");
        Console.WriteLine(JsonSerializer.Serialize(new {voice.API,voice.ID,voice.SpeakerName,output=path,bytes=new FileInfo(path).Length}));
    }
    Console.WriteLine("YMM4 public interface -> C# plugin -> persistent Python -> WAV: PASS");
}
