using System.Collections.Generic;
using UnityEngine;

// Star Catcher: catch falling stars, dodge bombs.
// Everything (sprites, objects, UI) is generated from code so the scene stays minimal.
public class GameManager : MonoBehaviour
{
    enum State { Title, Playing, GameOver }

    const float HalfWidth = 4.5f;
    const float PlayerY = -4f;
    const float PlayerSpeed = 9f;
    const float CatchRadius = 0.75f;

    State state = State.Title;
    Transform player;
    readonly List<Faller> fallers = new List<Faller>();
    Sprite circleSprite, starSprite, squareSprite;

    int score, lives, best;
    float elapsed, spawnTimer;
    float flashTimer;
    float stateTimer;
    SpriteRenderer playerRenderer;
    GUIStyle bigStyle, smallStyle;

    class Faller
    {
        public Transform t;
        public bool isBomb;
        public float speed;
        public float spin;
    }

    void Start()
    {
        best = PlayerPrefs.GetInt("best", 0);
        if (DemoRecorder.Active) { Random.InitState(7); best = 0; }

        var cam = Camera.main;
        cam.orthographic = true;
        cam.orthographicSize = 5f;
        cam.backgroundColor = new Color(0.05f, 0.06f, 0.15f);
        cam.clearFlags = CameraClearFlags.SolidColor;

        circleSprite = MakeSprite(64, (x, y) => x * x + y * y <= 1f);
        squareSprite = MakeSprite(8, (x, y) => true);
        starSprite = MakeSprite(64, IsInStar);

        // Background stars
        for (int i = 0; i < 60; i++)
        {
            var s = CreateSprite("BgStar", circleSprite, new Color(1, 1, 1, Random.Range(0.15f, 0.5f)), -10);
            s.transform.position = new Vector3(Random.Range(-9f, 9f), Random.Range(-5f, 5f), 0);
            s.transform.localScale = Vector3.one * Random.Range(0.03f, 0.08f);
        }

        // Ground
        var ground = CreateSprite("Ground", squareSprite, new Color(0.2f, 0.25f, 0.4f), -5);
        ground.transform.position = new Vector3(0, PlayerY - 0.55f, 0);
        ground.transform.localScale = new Vector3(HalfWidth * 2 + 1f, 0.15f, 1);

        // Player (a little round catcher)
        playerRenderer = CreateSprite("Player", circleSprite, new Color(0.35f, 0.85f, 1f), 0);
        player = playerRenderer.transform;
        player.position = new Vector3(0, PlayerY, 0);
        player.localScale = new Vector3(1.1f, 0.8f, 1);
    }

    void StartGame()
    {
        foreach (var f in fallers) Destroy(f.t.gameObject);
        fallers.Clear();
        score = 0;
        lives = 3;
        elapsed = 0;
        spawnTimer = 0.5f;
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

        // Movement: keyboard, or follow the mouse while button held
        float h = DemoRecorder.Active ? AutoPilot() : Input.GetAxisRaw("Horizontal");
        var p = player.position;
        if (!DemoRecorder.Active && Input.GetMouseButton(0))
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

        // Spawning gets faster over time
        float difficulty = 1f + elapsed / 20f;
        spawnTimer -= Time.deltaTime;
        if (spawnTimer <= 0)
        {
            Spawn(difficulty);
            spawnTimer = Mathf.Max(0.25f, 0.9f / difficulty);
        }

        // Fallers
        for (int i = fallers.Count - 1; i >= 0; i--)
        {
            var f = fallers[i];
            f.t.position += Vector3.down * f.speed * Time.deltaTime;
            f.t.Rotate(0, 0, f.spin * Time.deltaTime);

            if (Vector2.Distance(f.t.position, player.position) < CatchRadius)
            {
                if (f.isBomb)
                {
                    lives--;
                    flashTimer = 0.4f;
                    if (lives <= 0) GameOver();
                }
                else
                {
                    score += 10;
                }
                Remove(i);
                if (state != State.Playing) return;
            }
            else if (f.t.position.y < PlayerY - 1.5f)
            {
                Remove(i);
            }
        }

        // Hit flash
        if (flashTimer > 0)
        {
            flashTimer -= Time.deltaTime;
            playerRenderer.color = Color.Lerp(new Color(0.35f, 0.85f, 1f), Color.red, flashTimer / 0.4f);
        }
    }

    // Simple AI used in demo/recording mode: chase reachable stars, dodge incoming bombs.
    // After ~40 seconds it stops dodging so the recording also shows the game-over screen.
    float AutoPilot()
    {
        float px = player.position.x;
        bool careless = elapsed > 40f;

        // Target: the reachable star that arrives soonest
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

        // Score candidate positions near the player
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
                    // Would we be under this bomb when it lands, given travel along the way?
                    float lo = Mathf.Min(px, x), hi = Mathf.Max(px, x);
                    float bx = f.t.position.x;
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
        bool bomb = Random.value < Mathf.Min(0.5f, 0.25f + elapsed / 120f);
        var sr = bomb
            ? CreateSprite("Bomb", circleSprite, new Color(1f, 0.3f, 0.35f), 1)
            : CreateSprite("Star", starSprite, new Color(1f, 0.9f, 0.3f), 1);
        sr.transform.position = new Vector3(Random.Range(-HalfWidth, HalfWidth), 5.8f, 0);
        sr.transform.localScale = Vector3.one * (bomb ? 0.7f : 0.8f);
        fallers.Add(new Faller
        {
            t = sr.transform,
            isBomb = bomb,
            speed = Random.Range(2.5f, 4f) * difficulty,
            spin = bomb ? 0 : Random.Range(-180f, 180f)
        });
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
        playerRenderer.color = new Color(0.35f, 0.85f, 1f);
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
        if (bigStyle == null)
        {
            bigStyle = new GUIStyle(GUI.skin.label) { alignment = TextAnchor.MiddleCenter, fontStyle = FontStyle.Bold };
            smallStyle = new GUIStyle(GUI.skin.label) { alignment = TextAnchor.MiddleCenter };
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
                ? "Catch the stars, dodge the bombs!\n← → / A D / mouse to move"
                : $"Score {score}    Best {best}";
            GUI.Label(new Rect(0, hgt * 0.45f, w, hgt * 0.15f), info, smallStyle);
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

    // Builds a white sprite of size 1 world unit; shape test takes coords in [-1,1].
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
        // 5-point star: radius oscillates between outer and inner
        float k = Mathf.Abs(Mathf.Repeat(a * 5 / (2 * Mathf.PI), 1f) - 0.5f) * 2; // 1 at tips, 0 between
        float edge = Mathf.Lerp(0.45f, 1f, k);
        return r <= edge;
    }
}
