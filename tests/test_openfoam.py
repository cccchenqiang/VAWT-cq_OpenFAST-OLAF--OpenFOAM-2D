import tempfile
import unittest
from pathlib import Path

from core.openfoam.config import OpenFOAMCaseConfig
from core.openfoam.service import OpenFOAMCaseService


class OpenFOAMIntegrationTests(unittest.TestCase):
    def test_generate_case_from_isolated_template(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            airfoil = Path(temp) / "airfoil.txt"
            airfoil.write_text("0 0\n1 0\n0.5 0.1\n0 0\n", encoding="utf-8")
            output = Path(temp) / "case"
            config = OpenFOAMCaseConfig(str(airfoil), str(output))
            result = OpenFOAMCaseService(root).generate_case(config)
            self.assertEqual(result, output.resolve())
            self.assertTrue((result / "manifest.json").is_file())
            self.assertEqual(len(list((result / "constant" / "triSurface").glob("VAWT*.stl"))), 3)

    def test_existing_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            airfoil = Path(temp) / "airfoil.txt"
            airfoil.write_text("0 0\n1 0\n0.5 0.1\n", encoding="utf-8")
            output = Path(temp) / "case"
            output.mkdir()
            with self.assertRaises(FileExistsError):
                OpenFOAMCaseConfig(str(airfoil), str(output)).validate()


if __name__ == "__main__":
    unittest.main()
