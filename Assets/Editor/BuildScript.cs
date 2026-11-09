using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class BuildScript
{
    const string ScenePath = "Assets/Scenes/Main.unity";

    [MenuItem("StarCatcher/Create Main Scene")]
    public static void CreateScene()
    {
        System.IO.Directory.CreateDirectory("Assets/Scenes");
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

        var camGo = new GameObject("Main Camera");
        camGo.tag = "MainCamera";
        var cam = camGo.AddComponent<Camera>();
        cam.orthographic = true;
        camGo.transform.position = new Vector3(0, 0, -10);

        new GameObject("GameManager").AddComponent<GameManager>();

        EditorSceneManager.SaveScene(scene, ScenePath);
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
        AssetDatabase.SaveAssets();
    }

    // Extracts textures embedded in the AI-generated FBX models so their materials show color.
    [MenuItem("StarCatcher/Prepare AI Models")]
    public static void PrepareModels()
    {
        const string dir = "Assets/Resources/Models";
        if (!System.IO.Directory.Exists(dir)) return;
        foreach (var path in System.IO.Directory.GetFiles(dir, "*.fbx"))
        {
            var p = path.Replace('\\', '/');
            var name = System.IO.Path.GetFileNameWithoutExtension(p);
            var texDir = $"{dir}/Textures/{name}";
            if (System.IO.Directory.Exists(texDir)) continue;
            System.IO.Directory.CreateDirectory(texDir);
            var imp = (ModelImporter)AssetImporter.GetAtPath(p);
            imp.ExtractTextures(texDir);
            AssetDatabase.Refresh();
            imp.materialImportMode = ModelImporterMaterialImportMode.ImportStandard;
            imp.materialLocation = ModelImporterMaterialLocation.InPrefab;
            imp.materialSearch = ModelImporterMaterialSearch.Everywhere;
            imp.SaveAndReimport();
        }
    }

    [MenuItem("StarCatcher/Build Windows")]
    public static void BuildWindows()
    {
        PrepareModels();
        CreateScene();
        PlayerSettings.productName = "Star Catcher";
        PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
        PlayerSettings.runInBackground = true;
        PlayerSettings.defaultScreenWidth = 1280;
        PlayerSettings.defaultScreenHeight = 720;
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = new[] { ScenePath },
            locationPathName = "Build/StarCatcher.exe",
            target = BuildTarget.StandaloneWindows64,
            options = BuildOptions.None
        });
        Debug.Log("BUILD RESULT: " + report.summary.result);
        if (report.summary.result != UnityEditor.Build.Reporting.BuildResult.Succeeded)
            EditorApplication.Exit(1);
    }
}
