using UnityEngine;

// Command-line options:
//   -theme <0-3>        visual theme (0 Space, 1 Ocean, 2 Sakura, 3 Neon)
//   -ramp <seconds>     difficulty ramp (difficulty = 1 + time / ramp)
//   -simulate <N>       run N bot games as fast as possible and write results
//   -out <file.csv>     where -simulate writes its results
//   -record <dir>       autoplay and write a PNG per frame (see DemoRecorder)
public static class Settings
{
    public static int Theme;
    // Defaults tuned from 1,000 simulated bot games (see Promo/data): target median play >= 30s.
    public static float Ramp = 30f;
    public static float BombRate = 0.15f;   // base chance that a spawned object is a bomb
    public static int Simulate;
    public static string Out = "sim.csv";
    public static int Seed = 7;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
    static void Init()
    {
        var a = System.Environment.GetCommandLineArgs();
        for (int i = 0; i < a.Length - 1; i++)
        {
            switch (a[i])
            {
                case "-theme": int.TryParse(a[i + 1], out Theme); break;
                case "-ramp": float.TryParse(a[i + 1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out Ramp); break;
                case "-bomb": float.TryParse(a[i + 1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out BombRate); break;
                case "-simulate": int.TryParse(a[i + 1], out Simulate); break;
                case "-out": Out = a[i + 1]; break;
                case "-seed": int.TryParse(a[i + 1], out Seed); break;
            }
        }
        Theme = Mathf.Clamp(Theme, 0, Themes.All.Length - 1);
        if (Simulate > 0)
        {
            Time.captureDeltaTime = 1f / 30f;
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = -1;
        }
    }
}

public class Theme
{
    public string Name;
    public Color Bg, BgDot, Ground, Player, Good, Bad;
    public int Shape; // 0 star, 1 flower, 2 gem
}

public static class Themes
{
    public static readonly Theme[] All =
    {
        new Theme { Name = "SPACE",  Bg = new Color(0.05f, 0.06f, 0.15f), BgDot = Color.white,                     Ground = new Color(0.2f, 0.25f, 0.4f),  Player = new Color(0.35f, 0.85f, 1f), Good = new Color(1f, 0.9f, 0.3f),  Bad = new Color(1f, 0.3f, 0.35f), Shape = 0 },
        new Theme { Name = "OCEAN",  Bg = new Color(0.02f, 0.18f, 0.28f), BgDot = new Color(0.6f, 0.95f, 1f),      Ground = new Color(0.85f, 0.75f, 0.5f), Player = new Color(1f, 0.55f, 0.3f),  Good = new Color(0.5f, 1f, 0.9f),  Bad = new Color(0.45f, 0.2f, 0.55f), Shape = 2 },
        new Theme { Name = "SAKURA", Bg = new Color(0.98f, 0.9f, 0.92f),  BgDot = new Color(1f, 0.7f, 0.8f),       Ground = new Color(0.45f, 0.3f, 0.3f),  Player = new Color(0.35f, 0.6f, 0.4f), Good = new Color(1f, 0.5f, 0.7f),  Bad = new Color(0.25f, 0.25f, 0.3f), Shape = 1 },
        new Theme { Name = "NEON",   Bg = new Color(0.03f, 0.02f, 0.06f), BgDot = new Color(0.7f, 0.3f, 1f),       Ground = new Color(1f, 0.2f, 0.8f),     Player = new Color(0.2f, 1f, 0.6f),   Good = new Color(0.2f, 0.9f, 1f),  Bad = new Color(1f, 0.15f, 0.4f), Shape = 0 },
    };
}
