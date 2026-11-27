import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from image_generator import generate_recipe_image


class GenerateRecipeImageTests(unittest.TestCase):
    def test_returns_image_bytes_from_gemini_response(self):
        image_bytes = b"generated image"
        response = SimpleNamespace(
            parts=[
                SimpleNamespace(inline_data=None),
                SimpleNamespace(
                    inline_data=SimpleNamespace(data=image_bytes)
                ),
            ]
        )
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content=Mock(return_value=response))
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("image_generator.genai.Client", return_value=client) as gemini:
                result = generate_recipe_image("炒飯", ["白飯"])

        self.assertEqual(result, image_bytes)
        gemini.assert_called_once_with(api_key="test-key")
        self.assertEqual(
            client.models.generate_content.call_args.kwargs["model"],
            "gemini-nano-banana-2.1",
        )

    def test_errors_when_gemini_returns_no_image(self):
        response = SimpleNamespace(parts=[SimpleNamespace(inline_data=None)])
        client = SimpleNamespace(
            models=SimpleNamespace(generate_content=Mock(return_value=response))
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with patch("image_generator.genai.Client", return_value=client):
                with self.assertRaisesRegex(RuntimeError, "沒有回傳圖片"):
                    generate_recipe_image("炒飯", ["白飯"])


if __name__ == "__main__":
    unittest.main()
