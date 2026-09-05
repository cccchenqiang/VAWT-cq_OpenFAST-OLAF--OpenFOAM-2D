import tempfile
import unittest
from pathlib import Path

from core.cases.template import set_olaf_panels


class OlafVtkTests(unittest.TestCase):
    def test_tail_vtk_settings_are_written(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "OLAF.dat"
            path.write_text(
                "0 WrVTk\n3 nVTKBlades\n1 VTKCoord\n20 VTK_fps\n0 nGridOut\n",
                encoding="utf-8")
            set_olaf_panels(str(path), None, None, wr_vtk=0,
                            n_grid_out=0, n_vtk_blades=0,
                            vtk_coord=1, vtk_fps=20)
            text = path.read_text(encoding="utf-8")
            values = {line.split()[1]: line.split()[0]
                      for line in text.splitlines() if len(line.split()) >= 2}
            self.assertEqual(values["WrVTk"], "0")
            self.assertEqual(values["nVTKBlades"], "0")
            self.assertEqual(values["nGridOut"], "0")


if __name__ == "__main__":
    unittest.main()
