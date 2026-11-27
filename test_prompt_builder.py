import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from prompt_builder import build_recipe_prompt, generate_recipe


class GenerateRecipeRetryTests(unittest.TestCase):
    def setUp(self):
        self.conditions = {
            "cookware": ["快煮鍋"],
            "ingredients": ["肉鬆", "油豆腐"],
            "seasonings": ["食用油", "鹽", "醬油", "糖", "白胡椒粉", "蒜頭"],
            "preference": "一鍋到底懶人料理",
            "allow_extra_buy": False,
        }
        self.prompt = build_recipe_prompt(
            self.conditions["cookware"],
            self.conditions["ingredients"],
            self.conditions["seasonings"],
            self.conditions["preference"],
            self.conditions["allow_extra_buy"],
        )

    def test_rejects_non_ascii_api_key_before_request(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "換成你的 OpenAI API 金鑰"}):
            with patch("prompt_builder.OpenAI") as openai:
                with self.assertRaisesRegex(RuntimeError, "非 ASCII"):
                    generate_recipe(self.prompt)

        openai.assert_not_called()

    def _response(self, existing_ingredients):
        recipe = {
            "dish_name": "油豆腐肉鬆煮",
            "servings": 1,
            "time_minutes": 10,
            "preference": self.conditions["preference"],
            "cookware_used": ["快煮鍋"],
            "existing_ingredients": existing_ingredients,
            "used_seasonings": ["食用油", "鹽"],
            "suggested_purchases": [],
            "steps": [
                {
                    "step_number": 1,
                    "cookware": "快煮鍋",
                    "instruction": "將食材放入鍋中加熱。",
                }
            ],
            "reminders": [],
        }
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(recipe, ensure_ascii=False)
                    )
                )
            ]
        )

    def test_retries_with_allowed_ingredients_after_invalid_item(self):
        create = Mock(
            side_effect=[
                self._response(["白飯"]),
                self._response(["肉鬆", "油豆腐"]),
            ]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("prompt_builder.OpenAI", return_value=client):
                recipe = generate_recipe(self.prompt)

        self.assertEqual(recipe["existing_ingredients"], ["肉鬆", "油豆腐"])
        self.assertEqual(create.call_count, 2)
        retry_message = create.call_args_list[1].kwargs["messages"][1]["content"]
        self.assertIn('["肉鬆", "油豆腐"]', retry_message)

    def test_reports_invalid_item_after_retry_fails(self):
        create = Mock(
            side_effect=[
                self._response(["白飯"]),
                self._response(["白飯"]),
            ]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("prompt_builder.OpenAI", return_value=client):
                with self.assertRaisesRegex(ValueError, "白飯"):
                    generate_recipe(self.prompt)


if __name__ == "__main__":
    unittest.main()
