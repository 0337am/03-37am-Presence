from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def class_method(
    relative_path: str,
    class_name: str,
    method_name: str,
):
    path = (
        ROOT
        / relative_path
    )

    source = path.read_text(
        encoding="utf-8-sig"
    )

    tree = ast.parse(
        source,
        filename=str(path),
    )

    for node in tree.body:
        if not isinstance(
            node,
            ast.ClassDef,
        ):
            continue

        if node.name != class_name:
            continue

        for child in node.body:
            if (
                isinstance(
                    child,
                    ast.FunctionDef,
                )
                and child.name
                == method_name
            ):
                return child

    return None


class SpotifyActivationBoundaryTests(
    unittest.TestCase
):
    def test_spotify_page_does_not_use_show_event_for_loading(
        self,
    ):
        show_event = class_method(
            "src/ui/spotify_page.py",
            "SpotifyPage",
            "showEvent",
        )

        self.assertIsNone(
            show_event
        )

        activate = class_method(
            "src/ui/spotify_page.py",
            "SpotifyPage",
            "activate",
        )

        self.assertIsNotNone(
            activate
        )

    def test_main_window_activates_spotify_on_page_five(
        self,
    ):
        method = class_method(
            "src/ui/main_window.py",
            "MainWindow",
            "switch_page",
        )

        self.assertIsNotNone(
            method
        )

        page_five_blocks = []

        for node in ast.walk(
            method
        ):
            if not isinstance(
                node,
                ast.If,
            ):
                continue

            test = node.test

            if not isinstance(
                test,
                ast.Compare,
            ):
                continue

            if not isinstance(
                test.left,
                ast.Name,
            ):
                continue

            if test.left.id != "page_index":
                continue

            if len(
                test.comparators
            ) != 1:
                continue

            comparator = (
                test.comparators[0]
            )

            if (
                isinstance(
                    comparator,
                    ast.Constant,
                )
                and comparator.value == 5
            ):
                page_five_blocks.append(
                    node
                )

        self.assertTrue(
            page_five_blocks
        )

        calls_activate = False

        for block in page_five_blocks:
            for node in ast.walk(
                block
            ):
                if not isinstance(
                    node,
                    ast.Call,
                ):
                    continue

                function = node.func

                if (
                    isinstance(
                        function,
                        ast.Name,
                    )
                    and function.id
                    == "activate_spotify"
                ):
                    calls_activate = True

        self.assertTrue(
            calls_activate
        )
