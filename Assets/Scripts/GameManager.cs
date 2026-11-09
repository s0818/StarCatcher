using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

// Star Catcher: catch falling stars, dodge bombs.
// Visuals are generated from code; optional AI-generated 3D models and sounds are
// picked up automatically from Resources/Models and Resources/Audio when present.
public class GameManager : MonoBehaviour
{
    enum State { Title, Playing, GameOver }

    const float HalfWidth = 4.5f;
    const float PlayerY = -4f;
    const float PlayerSpeed = 9f;
    const float CatchRadius = 0.75f;
    const float SimTimeLimit = 300f;

    State state = State.Title;
    Transform player;
    readonly List<Faller> fallers = new List<Faller>();
    Sprite circleSprite, goodSprite, squareSprite;
    Theme theme;

    int score, lives, best;
    float elapsed, spawnTimer;
    float flashTimer;
    float stateTimer;
    Renderer playerRenderer;
    Color playerBaseColor;
    GUIStyle bigStyle, smallStyle;

    // Optional AI-generated assets
    GameObject goodModel, badModel, playerModel;
    readonly Dictionary<string, Material> texMats = new Dictionary<string, Material>();
    AudioSource sfx, music;
    AudioClip catchClip, hitClip, overClip, bgmClip;

    // Bot state
    bool BotActive => DemoRecorder.Active || Settings.Simulate > 0;
    float botTimer, botH;

    // Simulation results
    int simGame;
    readonly StringBuilder simCsv = new StringBuilder("game,ramp,bomb,score,survival_s,stars,hits\n");
    int stars, hits;

    class Faller
    {
        public Transform t;
        public bool isBomb;
        public float speed;
        public float spin;
        public float phase;
    }

    // ---- Rigged player (Meshy auto-rig: 24-bone humanoid + walk/run clips) ----
    Animation playerAnim;
    string idleClip;
    Transform hips;
    Vector3 hipsRest;
    float squashTimer;
    const float SquashTime = 0.35f;

    void SetupRig()
    {
        playerAnim = player.GetComponentInChildren<Animation>();
        if (!playerAnim) return;
        idleClip = playerAnim.clip ? playerAnim.clip.name : null;
        foreach (var (res, key) in new[] { ("Models/Anim/player_run", "run"), ("Models/Anim/player_walk", "walk") })
        {
            foreach (var c in Resources.LoadAll<AnimationClip>(res))
            {
                if (c.name.StartsWith("__preview")) continue;
                c.wrapMode = WrapMode.Loop;
                playerAnim.AddClip(c, key);
                break;
            }
        }
        foreach (var t in player.GetComponentsInChildren<Transform>())
            if (t.name == "Hips") { hips = t; hipsRest = t.localPosition; break; }
        playerAnim.cullingType = AnimationCullingType.AlwaysAnimate;
        if (idleClip != null) playerAnim.Play(idleClip);
        var names = new List<string>();
        foreach (AnimationState st in playerAnim) names.Add($"{st.name}({st.length:F2}s,legacy={st.clip.legacy})");
        Debug.Log($"RIG anim on '{playerAnim.gameObject.name}', idle={idleClip}, hips={(hips ? hips.name : "none")}, states: {string.Join(", ", names)}");
    }

    void UpdatePlayerAnimation(float h)
    {
        bool moving = Mathf.Abs(h) > 0.1f;
        // Face the run direction; turn back toward the camera when standing still.
        float yaw = moving ? (h > 0 ? 90f : 270f) : 180f;
        player.rotation = Quaternion.Slerp(player.rotation, Quaternion.Euler(0, yaw, 0), 1f - Mathf.Exp(-14f * Time.deltaTime));
        if (!playerAnim) return;
        if (moving && playerAnim["run"] != null)
        {
            playerAnim.CrossFade("run", 0.12f);
            playerAnim["run"].speed = Mathf.Lerp(0.8f, 1.3f, Mathf.Abs(h));
        }
        else if (idleClip != null) playerAnim.CrossFade(idleClip, 0.2f);
    }

    void LateUpdate()
    {
        if (!playerModel || player == null) return;
        // Clips carry root motion on the hips: pin them horizontally so the character runs in place.
        if (hips) hips.localPosition = new Vector3(hipsRest.x, hips.localPosition.y, hipsRest.z);
        // Squash-and-stretch hit reaction (procedural, no extra clip needed)
        if (squashTimer > 0)
        {
            squashTimer -= Time.deltaTime;
            float a = squashTimer / SquashTime;
            float s = Mathf.Sin(a * Mathf.PI) * 0.35f;
            player.localScale = new Vector3(1f + s * 0.6f, 1f - s, 1f + s * 0.6f);
        }
        else
        {
            // Subtle idle "breathing" so the rest pose never looks frozen
            float b = Mathf.Sin(Time.time * 3f) * 0.015f;
            player.localScale = new Vector3(1f - b * 0.5f, 1f + b, 1f - b * 0.5f);
        }
    }

    void Start()
    {
        theme = Themes.All[Settings.Theme];
        best = PlayerPrefs.GetInt("best", 0);
        if (BotActive) { Random.InitState(Settings.Seed); best = 0; }

        var cam = Camera.main;
        cam.orthographic = true;
        cam.orthographicSize = 5f;
        cam.backgroundColor = theme.Bg;
        cam.clearFlags = CameraClearFlags.SolidColor;

        circleSprite = MakeSprite(64, (x, y) => x * x + y * y <= 1f);
        squareSprite = MakeSprite(8, (x, y) => true);
        goodSprite = MakeSprite(64, theme.Shape == 1 ? IsInFlower : theme.Shape == 2 ? (System.Func<float, float, bool>)IsInGem : IsInStar);

        goodModel = Resources.Load<GameObject>("Models/good");
        badModel = Resources.Load<GameObject>("Models/bad");
        playerModel = Resources.Load<GameObject>("Models/player");
        if (goodModel || badModel || playerModel)
        {
            var light = new GameObject("Light").AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.4f;
            light.transform.rotation = Quaternion.Euler(35, -30, 0);
            RenderSettings.ambientLight = new Color(0.75f, 0.75f, 0.8f);
        }

        if (Settings.Simulate == 0)
        {
            sfx = gameObject.AddComponent<AudioSource>();
            music = gameObject.AddComponent<AudioSource>();
            music.loop = true; music.volume = 0.45f;
            catchClip = Resources.Load<AudioClip>("Audio/catch");
            hitClip = Resources.Load<AudioClip>("Audio/hit");
            overClip = Resources.Load<AudioClip>("Audio/gameover");
            bgmClip = Resources.Load<AudioClip>("Audio/bgm");
            if (bgmClip) { music.clip = bgmClip; music.Play(); }
        }

        // Background dots
        for (int i = 0; i < 60; i++)
        {
            var c = theme.BgDot; c.a = Random.Range(0.15f, 0.5f);
            var s = CreateSprite("BgDot", circleSprite, c, -10);
            s.transform.position = new Vector3(Random.Range(-9f, 9f), Random.Range(-5f, 5f), 0);
            s.transform.localScale = Vector3.one * Random.Range(0.03f, 0.08f);
        }

        // Ground
        var ground = CreateSprite("Ground", squareSprite, theme.Ground, -5);
        ground.transform.position = new Vector3(0, PlayerY - 0.55f, 0);
        ground.transform.localScale = new Vector3(HalfWidth * 2 + 1f, 0.15f, 1);

        // Player
        if (playerModel)
        {
            player = Instantiate3D(playerModel, 1.7f).transform;
            playerRenderer = player.GetComponentInChildren<Renderer>();
            SetupRig();
        }
        else
        {
            var sr = CreateSprite("Player", circleSprite, theme.Player, 0);
            player = sr.transform;
            player.localScale = new Vector3(1.1f, 0.8f, 1);
            playerRenderer = sr;
        }
        playerBaseColor = playerRenderer.material.HasProperty("_Color") ? playerRenderer.material.color : Color.white;
        player.position = new Vector3(0, PlayerY, 0);

        if (Settings.Simulate > 0) StartGame();
    }

    void StartGame()
    {
        foreach (var f in fallers) Destroy(f.t.gameObject);
        fallers.Clear();
        score = 0; stars = 0; hits = 0;
        lives = 3;
        elapsed = 0;
        spawnTimer = 0.5f;
        botTimer = 0; botH = 0;
        player.position = new Vector3(0, PlayerY, 0);
        state = State.Playing;
    }

    void Update()
    {
        bool action = Input.GetKeyDown(KeyCode.Space) || Input.GetKeyDown(KeyCode.Return) || Input.GetMouseButtonDown(0);
        if (Input.GetKeyDown(KeyCode.Escape)) Application.Quit();

        if (state != State.Playing)
        {
            if (DemoRecorder.Active)
            {
                stateTimer += Time.deltaTime;
                if (state == State.Title && stateTimer > 3f) action = true;
                if (state == State.GameOver && stateTimer > 4f) { Application.Quit(); return; }
            }
            if (action && state == State.Title) StartGame();
            else if (action && !DemoRecorder.Active) StartGame();
            return;
        }

        elapsed += Time.deltaTime;

        float h = BotActive ? BotInput() : Input.GetAxisRaw("Horizontal");
        var p = player.position;
        if (!BotActive && Input.GetMouseButton(0))
        {
            float mx = Camera.main.ScreenToWorldPoint(Input.mousePosition).x;
            p.x = Mathf.MoveTowards(p.x, mx, PlayerSpeed * Time.deltaTime);
        }
        else
        {
            p.x += h * PlayerSpeed * Time.deltaTime;
        }
        p.x = Mathf.Clamp(p.x, -HalfWidth, HalfWidth);
        player.position = p;
        if (playerModel) UpdatePlayerAnimation(h);

        // Spawning gets faster over time
        float difficulty = 1f + elapsed / Settings.Ramp;
        spawnTimer -= Time.deltaTime;
        if (spawnTimer <= 0)
        {
            Spawn(difficulty);
            spawnTimer = Mathf.Max(0.25f, 0.9f / difficulty);
        }

        for (int i = fallers.Count - 1; i >= 0; i--)
        {
            var f = fallers[i];
            f.t.position += Vector3.down * f.speed * Time.deltaTime;
            if (f.t.GetComponent<SpriteRenderer>()) f.t.Rotate(0, 0, f.spin * Time.deltaTime);
            else
            {
                // Bone-less procedural animation for non-humanoid props
                f.t.Rotate(0, f.spin * Time.deltaTime, 0, Space.World);
                float k = Mathf.InverseLerp(5.8f, PlayerY, f.t.position.y); // 0 at top -> 1 near the ground
                if (f.isBomb)
                {
                    // the bomb wobbles faster and swells as it gets closer ("about to blow")
                    float w = Mathf.Sin((elapsed + f.phase) * Mathf.Lerp(6f, 22f, k));
                    f.t.localScale = Vector3.one * (1f + 0.08f * k * Mathf.Abs(w));
                    f.t.rotation = Quaternion.Euler(15, f.t.eulerAngles.y, w * 10f);
                }
                else
                {
                    // the star pulses like a twinkle
                    f.t.localScale = Vector3.one * (1f + 0.07f * Mathf.Sin((elapsed + f.phase) * 9f));
                }
            }

            if (Vector2.Distance(f.t.position, player.position) < CatchRadius)
            {
                if (f.isBomb)
                {
                    lives--; hits++;
                    flashTimer = 0.4f;
                    squashTimer = SquashTime;
                    Play(hitClip);
                    if (lives <= 0) GameOver();
                }
                else
                {
                    score += 10; stars++;
                    Play(catchClip, 0.6f);
                }
                Remove(i);
                if (state != State.Playing) return;
            }
            else if (f.t.position.y < PlayerY - 1.5f)
            {
                Remove(i);
            }
        }

        if (Settings.Simulate > 0 && elapsed > SimTimeLimit) { GameOver(); return; }

        if (flashTimer > 0)
        {
            flashTimer -= Time.deltaTime;
            playerRenderer.material.color = Color.Lerp(playerBaseColor, Color.red, flashTimer / 0.4f);
        }
    }

    void Play(AudioClip c, float vol = 1f) { if (sfx && c) sfx.PlayOneShot(c, vol); }

    // Bot input. In recording mode it plays sharply (and gets careless after 40s so the
    // video shows a game over). In simulation mode it behaves like a human player:
    // it re-decides only every ~0.2s and misjudges positions slightly.
    float BotInput()
    {
        if (DemoRecorder.Active) return AutoPilot(elapsed > 40f, 0f);
        botTimer -= Time.deltaTime;
        if (botTimer <= 0)
        {
            botTimer = Random.Range(0.15f, 0.28f);
            botH = AutoPilot(false, 0.45f);
        }
        return botH;
    }

    float AutoPilot(bool careless, float error)
    {
        float px = player.position.x;

        float targetX = 0f;
        float bestT = float.MaxValue;
        foreach (var f in fallers)
        {
            if (f.isBomb) continue;
            float dy = f.t.position.y - PlayerY;
            if (dy < -0.3f) continue;
            float t = dy / f.speed;
            if (Mathf.Abs(f.t.position.x - px) > PlayerSpeed * t + CatchRadius) continue;
            if (t < bestT) { bestT = t; targetX = f.t.position.x; }
        }

        float bestX = px, bestCost = float.MaxValue;
        for (float x = -HalfWidth; x <= HalfWidth + 0.01f; x += 0.25f)
        {
            float cost = Mathf.Abs(x - targetX) * 0.3f + Mathf.Abs(x - px) * 0.05f;
            if (!careless)
            {
                foreach (var f in fallers)
                {
                    if (!f.isBomb) continue;
                    float dy = f.t.position.y - PlayerY;
                    if (dy < -0.5f) continue;
                    float t = dy / f.speed;
                    if (t > 1.2f) continue;
                    float lo = Mathf.Min(px, x), hi = Mathf.Max(px, x);
                    float bx = f.t.position.x + (error > 0 ? Random.Range(-error, error) : 0f);
                    float pathDist = bx < lo ? lo - bx : bx > hi ? bx - hi : 0f;
                    if (Mathf.Abs(bx - x) < 1.1f) cost += 100f;
                    else if (pathDist < 1.0f && t < 0.5f) cost += 30f;
                }
            }
            if (cost < bestCost) { bestCost = cost; bestX = x; }
        }

        float diff = bestX - px;
        if (Mathf.Abs(diff) < 0.1f) return 0f;
        return Mathf.Clamp(diff * 3f, -1f, 1f);
    }

    void Spawn(float difficulty)
    {
        bool bomb = Random.value < Mathf.Min(0.5f, Settings.BombRate + elapsed / 120f);
        Transform t;
        var model = bomb ? badModel : goodModel;
        if (model)
        {
            t = Instantiate3D(model, bomb ? 1.0f : 1.15f).transform;
            t.rotation = Quaternion.Euler(15, Random.Range(0, 360f), 0);
        }
        else
        {
            var sr = bomb
                ? CreateSprite("Bomb", circleSprite, theme.Bad, 1)
                : CreateSprite("Good", goodSprite, theme.Good, 1);
            sr.transform.localScale = Vector3.one * (bomb ? 0.7f : 0.8f);
            t = sr.transform;
        }
        t.position = new Vector3(Random.Range(-HalfWidth, HalfWidth), 5.8f, 0);
        fallers.Add(new Faller
        {
            t = t,
            isBomb = bomb,
            speed = Random.Range(2.5f, 4f) * difficulty,
            spin = model ? Random.Range(60f, 140f) : (bomb ? 0 : Random.Range(-180f, 180f)),
            phase = Random.Range(0f, 10f)
        });
    }

    // Instantiates a model and scales it so its largest dimension equals `size` world units.
    GameObject Instantiate3D(GameObject prefab, float size)
    {
        var root = new GameObject(prefab.name);
        var go = Instantiate(prefab, root.transform);
        var rs = go.GetComponentsInChildren<Renderer>();
        // Apply the AI-generated texture (extracted from the FBX into Resources/Models/Textures/<name>)
        var tex = Resources.Load<Texture2D>($"Models/Textures/{prefab.name}/Image_0");
        if (tex)
        {
            if (!texMats.TryGetValue(prefab.name, out var mat))
            {
                mat = new Material(Shader.Find("Standard")) { mainTexture = tex };
                mat.SetFloat("_Glossiness", 0.35f);
                texMats[prefab.name] = mat;
            }
            foreach (var r in rs) r.sharedMaterial = mat;
        }
        if (rs.Length > 0)
        {
            var b = rs[0].bounds;
            foreach (var r in rs) b.Encapsulate(r.bounds);
            float m = Mathf.Max(b.size.x, b.size.y, b.size.z);
            if (m > 0) go.transform.localScale *= size / m;
            b = rs[0].bounds;
            foreach (var r in rs) b.Encapsulate(r.bounds);
            go.transform.position -= b.center - root.transform.position;
        }
        return root;
    }

    void Remove(int i)
    {
        Destroy(fallers[i].t.gameObject);
        fallers.RemoveAt(i);
    }

    void GameOver()
    {
        state = State.GameOver;
        stateTimer = 0;
        playerRenderer.material.color = playerBaseColor;
        Play(overClip);
        if (music) music.Stop();

        if (Settings.Simulate > 0)
        {
            simGame++;
            simCsv.AppendLine(string.Format(System.Globalization.CultureInfo.InvariantCulture,
                "{0},{1},{2},{3},{4:F2},{5},{6}", simGame, Settings.Ramp, Settings.BombRate, score, elapsed, stars, hits));
            if (simGame >= Settings.Simulate)
            {
                File.WriteAllText(Settings.Out, simCsv.ToString());
                Application.Quit();
            }
            else StartGame();
            return;
        }

        if (score > best && DemoRecorder.Active) best = score;
        else if (score > best)
        {
            best = score;
            PlayerPrefs.SetInt("best", best);
            PlayerPrefs.Save();
        }
    }

    void OnGUI()
    {
        if (Settings.Simulate > 0) return;
        if (bigStyle == null)
        {
            bigStyle = new GUIStyle(GUI.skin.label) { alignment = TextAnchor.MiddleCenter, fontStyle = FontStyle.Bold };
            smallStyle = new GUIStyle(GUI.skin.label) { alignment = TextAnchor.MiddleCenter };
            var txt = theme.Bg.grayscale > 0.5f ? new Color(0.2f, 0.15f, 0.2f) : new Color(0.95f, 0.95f, 1f);
            bigStyle.normal.textColor = txt; smallStyle.normal.textColor = txt;
        }
        bigStyle.fontSize = Screen.height / 10;
        smallStyle.fontSize = Screen.height / 28;
        float w = Screen.width, hgt = Screen.height;

        var hud = new GUIStyle(smallStyle) { alignment = TextAnchor.UpperLeft };
        if (state == State.Playing)
        {
            GUI.Label(new Rect(16, 12, w, 60), $"SCORE {score}", hud);
            hud.alignment = TextAnchor.UpperRight;
            GUI.Label(new Rect(0, 12, w - 16, 60), $"LIFE {Mathf.Max(0, lives)}", hud);
        }
        else
        {
            string title = state == State.Title ? "STAR CATCHER" : "GAME OVER";
            GUI.Label(new Rect(0, hgt * 0.25f, w, hgt * 0.15f), title, bigStyle);
            string info = state == State.Title
                ? $"- {theme.Name} -\nCatch the stars, dodge the bombs!\n<- -> / A D / mouse to move"
                : $"Score {score}    Best {best}";
            GUI.Label(new Rect(0, hgt * 0.42f, w, hgt * 0.2f), info, smallStyle);
            GUI.Label(new Rect(0, hgt * 0.65f, w, hgt * 0.1f), "Press SPACE or click to start", smallStyle);
        }
    }

    // ---- helpers ----

    SpriteRenderer CreateSprite(string name, Sprite sprite, Color color, int order)
    {
        var go = new GameObject(name);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = sprite;
        sr.color = color;
        sr.sortingOrder = order;
        return sr;
    }

    static Sprite MakeSprite(int size, System.Func<float, float, bool> inside)
    {
        var tex = new Texture2D(size, size, TextureFormat.RGBA32, false) { filterMode = FilterMode.Bilinear };
        var px = new Color32[size * size];
        for (int y = 0; y < size; y++)
            for (int x = 0; x < size; x++)
            {
                float u = (x + 0.5f) / size * 2 - 1, v = (y + 0.5f) / size * 2 - 1;
                px[y * size + x] = inside(u, v) ? new Color32(255, 255, 255, 255) : new Color32(255, 255, 255, 0);
            }
        tex.SetPixels32(px);
        tex.Apply();
        return Sprite.Create(tex, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f), size);
    }

    static bool IsInStar(float x, float y)
    {
        float r = Mathf.Sqrt(x * x + y * y);
        float a = Mathf.Atan2(y, x) + Mathf.PI / 2;
        float k = Mathf.Abs(Mathf.Repeat(a * 5 / (2 * Mathf.PI), 1f) - 0.5f) * 2;
        return r <= Mathf.Lerp(0.45f, 1f, k);
    }

    static bool IsInFlower(float x, float y)
    {
        float r = Mathf.Sqrt(x * x + y * y);
        float a = Mathf.Atan2(y, x) + Mathf.PI / 2;
        return r <= 0.55f + 0.45f * Mathf.Abs(Mathf.Cos(a * 2.5f));
    }

    static bool IsInGem(float x, float y) => Mathf.Abs(x) * 1.3f + Mathf.Abs(y) <= 1f;
}
