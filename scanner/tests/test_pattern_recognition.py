import unittest
import os
import tempfile
import shutil
from app import TodoItem, find_todos
from unittest.mock import patch

class TestTodoPatternRecognition(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for our test repository
        self.test_repo_path = tempfile.mkdtemp()
        
    def tearDown(self):
        # Clean up the temporary directory
        shutil.rmtree(self.test_repo_path)
        
    def create_test_file(self, file_name, content):
        file_path = os.path.join(self.test_repo_path, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
        
    @patch('app.is_git_ignored')
    @patch('app.is_text_file')
    def test_basic_todo_patterns(self, mock_is_text_file, mock_is_git_ignored):
        # Make sure our file is treated as a text file and not git ignored
        mock_is_text_file.return_value = True
        mock_is_git_ignored.return_value = False
        
        # Create a test file with various TODO comment formats
        test_content = """
        # TODO: Fix this function
        // TODO: Update documentation
        /* TODO: Review algorithm */
        <!-- TODO: Update HTML -->
        # FIXME: This is broken
        // FIXME: Need to refactor
        # BUG: This crashes under certain conditions
        /* NOTE: Important implementation detail */
        """
        
        self.create_test_file('test_code.txt', test_content)
        
        # With the current implementation, only some patterns should be found
        todos = list(find_todos(self.test_repo_path))
        
        # Current implementation only recognizes # TODO, // TODO, and TODO: patterns
        # This test should initially fail, showing only 3 TODOs found instead of all 8
        self.assertEqual(len(todos), 8, "Should find all eight TODO patterns")
        
        # Verify that the correct TODO texts are found
        todo_texts = [todo.todo_text.strip() for todo in todos]
        expected_patterns = [
            "# TODO: Fix this function",
            "// TODO: Update documentation",
            "/* TODO: Review algorithm */",
            "<!-- TODO: Update HTML -->",
            "# FIXME: This is broken",
            "// FIXME: Need to refactor",
            "# BUG: This crashes under certain conditions",
            "/* NOTE: Important implementation detail */"
        ]
        
        for expected_pattern in expected_patterns:
            self.assertTrue(
                any(expected_pattern in text for text in todo_texts),
                f"Could not find expected pattern: {expected_pattern}"
            )

if __name__ == '__main__':
    unittest.main()