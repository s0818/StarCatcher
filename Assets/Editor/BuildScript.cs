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

    [MenuItem("StarCatcher/Build Windows")]
    public static void BuildWindows()
    {
        CreateScene();
        PlayerSettings.productName = "Star Catcher";
        PlayerSettings.fullScreenMode = FullScreenMode.Windowed;
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
