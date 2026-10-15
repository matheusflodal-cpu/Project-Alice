# UWP / Xbox port status

The desktop Alice executable is **not yet a UWP game**. Defining
`WINAPI_FAMILY_DESKTOP_APP` or removing AppContainer does not port desktop APIs.
The old workflow did both; these overrides must not be used for shipping.

## Diagnostic application

`python tools/uwp/build_probe.py` builds an x64 AppContainer application and an
unsigned `build_uwp_probe/AliceUwpProbe.msix` with the installed Visual Studio
2022 C++ tools and Windows 10 SDK. This application is deliberately separate
from the Alice executable. It exercises CoreWindow, Direct3D 11, XAudio2 and
ApplicationData.LocalFolder without using the desktop API family. It displays
a blue window and writes `uwp-probe.txt` into its own LocalState directory.
It does not load scenarios, render the map or play the game.

The package needs signing with a trusted certificate whose subject matches
`CN=ProjectAliceDevelopment` before normal sideloading. No private signing key
is included or uploaded. The Release UWP x64 VC runtime dependency must also
be installed on the target. Validate deployment and the diagnostics on Xbox
Developer Mode; a successful compile/package is not a successful console test.

## Remaining engine blockers

* `src/platform_specific.cpp` selects all desktop backends on `_WIN64`.
* `src/window/window_win.cpp` uses HWND, window messages and desktop input.
* `src/graphics/opengl_wrapper_win.cpp` requests OpenGL 4.6 through WGL/GLEW.
  A CoreWindow-compatible graphics backend or verified UWP translation layer
  is needed; OpenGL ES is not a drop-in replacement for desktop OpenGL 4.6.
  `assets/shaders/glsl/_geometry.glsl` also declares GLSL 4.60. One candidate
  to investigate is [Mesa UWP](https://github.com/aerisarn/mesa-uwp), whose fork
  documents a UWP build. It has not been built or validated against Alice here;
  its existence does not establish shader/API compatibility or Xbox performance.
* `src/sound/sound_win.cpp` uses DirectShow. XAudio2 still needs decoding,
  streaming, volume and lifetime integration into Alice's sound interface.
* `src/filesystem/simple_fs_win.cpp` resolves desktop Documents/AppData paths.
  Package assets must be read-only and saves/settings/scenarios must use the
  application's LocalState, including the paths embedded in scenario data.
* Prebuilt `libs/LLVM-C.lib` and `libs/luajit.lib` have not been validated for
  AppContainer. JIT/dynamic-code assumptions must be audited independently.
* Controller input, suspension/resumption, display changes, device loss,
  memory budgets and scenario compatibility still need console tests.

Host code generators belong to a separate desktop build. The workflow builds
them first with `ALICE_HOST_TOOLS_ONLY=ON`, then imports their executable paths
using `ALICE_HOST_TOOLS_DIR` and runs them during the strict UWP compile.
The engine compile remains a diagnostic job and is expected to expose real
unsupported APIs until the backends are ported. Its failure is not suppressed.

References: [CoreApplication/IFrameworkView](https://learn.microsoft.com/en-us/uwp/api/windows.applicationmodel.core.iframeworkview),
[UWP packaging](https://learn.microsoft.com/en-us/windows/msix/package/create-app-package-with-makeappx-tool).
