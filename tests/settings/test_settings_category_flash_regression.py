from __future__ import annotations

import ast
import unittest
from pathlib import Path


class SettingsCategoryFlashRegressionTests(
    unittest.TestCase
):
    def test_normal_category_buttons_bypass_deep_link_path(
        self,
    ):
        source = Path(
            "src/ui/settings.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        tree = ast.parse(
            source
        )

        cls = next(
            node
            for node in tree.body
            if (
                isinstance(
                    node,
                    ast.ClassDef,
                )
                and node.name
                == "SettingsPage"
            )
        )

        build = next(
            node
            for node in cls.body
            if (
                isinstance(
                    node,
                    ast.FunctionDef,
                )
                and node.name
                == "build_ui"
            )
        )

        legacy = []
        direct = []

        for node in ast.walk(
            build
        ):
            if not isinstance(
                node,
                ast.Lambda,
            ):
                continue

            attrs = {
                child.attr
                for child
                in ast.walk(
                    node
                )
                if isinstance(
                    child,
                    ast.Attribute,
                )
            }

            names = {
                child.id
                for child
                in ast.walk(
                    node
                )
                if isinstance(
                    child,
                    ast.Name,
                )
            }

            args = {
                item.arg
                for item
                in node.args.args
            }

            if (
                "show_section"
                in attrs
                and "section_target"
                in names
            ):
                legacy.append(
                    node
                )

            if (
                "_set_active_settings_category"
                in attrs
                and "category"
                in args
            ):
                direct.append(
                    node
                )

        self.assertEqual(
            legacy,
            [],
        )

        self.assertGreaterEqual(
            len(
                direct
            ),
            1,
        )

    def test_true_deep_link_support_remains(
        self,
    ):
        source = Path(
            "src/ui/settings.py"
        ).read_text(
            encoding="utf-8-sig"
        )

        self.assertIn(
            "def show_section(",
            source,
        )

        self.assertIn(
            "self._highlight_settings_card(",
            source,
        )


if __name__ == "__main__":
    unittest.main()
