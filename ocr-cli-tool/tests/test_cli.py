import unittest
import sys
from pathlib import Path
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.cli import main

class TestCli(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    def test_command_line_interface(self):
        result = self.runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert 'Usage:' in result.output

    def test_ocr_functionality(self):
        result = self.runner.invoke(main, ['--input', 'test_image.png'])
        assert result.exit_code == 0
        assert 'OCR result:' in result.output

    def test_invalid_input(self):
        result = self.runner.invoke(main, ['--input', 'invalid_image.txt'])
        assert result.exit_code != 0
        assert 'Error:' in result.output

if __name__ == '__main__':
    unittest.main()