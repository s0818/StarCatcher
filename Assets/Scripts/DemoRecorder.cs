using System.IO;
using UnityEngine;

// Demo/recording mode for making promo videos.
// Launch with:  StarCatcher.exe -record <outputDir>
// The game plays itself (autopilot) and writes one PNG per frame at a fixed 30 fps.
public class DemoRecorder : MonoBehaviour
{
    public static bool Active { get; private set; }
    public static string OutputDir { get; private set; }

    const int Fps = 30;
    int frame;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
    static void Init()
    {
        var args = System.Environment.GetCommandLineArgs();
        for (int i = 0; i < args.Length - 1; i++)
        {
            if (args[i] == "-record")
            {
                Active = true;
                OutputDir = args[i + 1];
                Directory.CreateDirectory(OutputDir);
                Time.captureFramerate = Fps;
                var go = new GameObject("DemoRecorder");
                DontDestroyOnLoad(go);
                go.AddComponent<DemoRecorder>();
            }
        }
    }

    static int maxFrames = int.MaxValue;

    void Start()
    {
        var args = System.Environment.GetCommandLineArgs();
        for (int i = 0; i < args.Length - 1; i++)
            if (args[i] == "-frames") int.TryParse(args[i + 1], out maxFrames);
    }

    void LateUpdate()
    {
        if (frame >= maxFrames) { Application.Quit(); return; }
        ScreenCapture.CaptureScreenshot(Path.Combine(OutputDir, $"f{frame:D5}.png"));
        frame++;
    }
}
