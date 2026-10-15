"""Regression checks for API restrictions and host-tool selection (stdlib only)."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

from prepare import prepare

ROOT = Path(__file__).resolve().parents[2]


class PreparationTests(unittest.TestCase):
    def test_dynamic_crt_preserves_appcontainer_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "Alice.vcxproj"
            path.write_text('''<Project><PropertyGroup>
<ApplicationType>Windows Store</ApplicationType>
<AppContainerApplication>true</AppContainerApplication>
</PropertyGroup><ItemDefinitionGroup><ClCompile>
<RuntimeLibrary>MultiThreaded</RuntimeLibrary>
</ClCompile></ItemDefinitionGroup></Project>''')
            prepare(folder)
            once = path.read_text()
            prepare(folder)
            self.assertEqual(once, path.read_text())
            root = ET.fromstring(once)
            self.assertEqual(root.findtext(".//RuntimeLibrary"), "MultiThreadedDLL")
            self.assertEqual(root.findtext(".//AppContainerApplication"), "true")
            self.assertEqual(root.findtext(".//ApplicationType"), "Windows Store")

    def test_no_projects_is_an_error(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(RuntimeError):
                prepare(folder)

    @unittest.skipUnless(os.environ.get("CMAKE_EXE"), "Set CMAKE_EXE for CMake integration checks")
    def test_cross_build_requires_and_selects_desktop_executables(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)
            module = (ROOT / 'cmake/HostGenerators.cmake').as_posix()
            (source / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.16)\n'
                'project(HostSelection NONE)\nset(CMAKE_SYSTEM_NAME WindowsStore)\n'
                f'include("{module}")\n'
                'file(GENERATE OUTPUT "${CMAKE_BINARY_DIR}/selected.txt" CONTENT "$<TARGET_FILE:${ALICE_TOOL_ParserGenerator}>")\n')
            command = [os.environ['CMAKE_EXE'], '-S', str(source), '-B', str(source / 'build')]
            missing = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn('UWP requires ALICE_HOST_TOOLS_DIR', missing.stdout + missing.stderr)
            host = source / 'desktop tools'
            host.mkdir()
            for name in ('ParserGenerator', 'DCONGENERATOR', 'DCONINTERFACEGEN',
                         'DataContainer-Lua', 'DataContainer_OOS_Reporter'):
                (host / (name + '.exe')).touch()
            complete = subprocess.run(command + ['-DALICE_HOST_TOOLS_DIR=' + host.as_posix()],
                                      capture_output=True, text=True)
            self.assertEqual(complete.returncode, 0, complete.stdout + complete.stderr)
            selected = (source / 'build/selected.txt').read_text()
            # Hosted runners can expose TEMP through an 8.3 path alias while
            # CMake expands it. Compare file identity rather than path spelling.
            self.assertTrue(Path(selected).samefile(host / 'ParserGenerator.exe'))


if __name__ == '__main__':
    unittest.main()
