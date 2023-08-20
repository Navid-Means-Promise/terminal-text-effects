from terminaltexteffects.utils import ansicodes, colorterm
from terminaltexteffects.base_character import EffectCharacter
import shutil
import sys
from dataclasses import dataclass


@dataclass
class OutputArea:
    """A class for storing the output area of an effect.

    Args:
        top (int): top row of the output area
        right (int): right column of the output area
        bottom (int): bottom row of the output area. Defaults to 1.
        left (int): left column of the output area. Defaults to 1.

    """

    top: int
    right: int
    bottom: int = 1
    left: int = 1


class Terminal:
    def __init__(self, input_data: str):
        self.input_data = input_data
        self.width, self.height = self._get_terminal_dimensions()
        self.characters = self._decompose_input()
        self.input_width = max([character.input_coord.column for character in self.characters])
        self.input_height = max([character.input_coord.row for character in self.characters])
        self.output_area = OutputArea(min(self.height - 1, self.input_height), self.input_width)
        self.characters = [
            character for character in self.characters if character.input_coord.row <= self.output_area.top
        ]
        self._update_terminal_state()

        self._prep_outputarea()

    def _get_terminal_dimensions(self) -> tuple[int, int]:
        """Returns the terminal dimensions.

        Returns:
            tuple[int, int]: width, height
        """
        terminal_width, terminal_height = shutil.get_terminal_size()
        return terminal_width, terminal_height

    @staticmethod
    def get_piped_input() -> str:
        """Gets the piped input from stdin.

        Returns:
            str: string from stdin
        """
        if not sys.stdin.isatty():
            input_data = sys.stdin.read()
            return input_data
        else:
            return ""

    def _decompose_input(self) -> list[EffectCharacter]:
        """Decomposes the output into a list of Character objects containing the symbol and its row/column coordinates
        relative to the input display location.

        Coordinates are relative to the cursor row position at the time of execution. 1,1 is the bottom left corner of the row
        above the cursor.

        Returns:
            list[Character]: list of EffectCharacter objects
        """
        wrapped_lines = []
        input_lines = self.input_data.splitlines()
        for line in input_lines:
            while len(line) > self.width:
                wrapped_lines.append(line[: self.width])
                line = line[self.width :]
            if line:
                wrapped_lines.append(line)
        input_height = len(wrapped_lines)
        input_characters = []
        for row, line in enumerate(wrapped_lines):
            for column, symbol in enumerate(line):
                if symbol != " ":
                    input_characters.append(EffectCharacter(symbol, column + 1, input_height - row))
        return input_characters

    def _update_terminal_state(self):
        """Update the internal representation of the terminal state with the current position
        of all active characters.
        """
        rows = [[" " for _ in range(self.output_area.right)] for _ in range(self.output_area.top)]
        for character in self.characters:
            if character.is_active:
                rows[character.current_coord.row - 1][character.current_coord.column - 1] = character.symbol
        terminal_state = ["".join(row) for row in rows]
        self.terminal_state = terminal_state

    def _prep_outputarea(self) -> None:
        """Prepares the terminal for the effect by adding empty lines above."""
        print("\n" * self.output_area.top)

    def print(self):
        self._update_terminal_state()
        for row_index, row in enumerate(self.terminal_state):
            sys.stdout.write(ansicodes.DEC_SAVE_CURSOR_POSITION())
            sys.stdout.write(ansicodes.MOVE_CURSOR_UP(row_index + 1))
            sys.stdout.write(ansicodes.MOVE_CURSOR_TO_COLUMN(1))
            sys.stdout.write(row)
            sys.stdout.write(ansicodes.DEC_RESTORE_CURSOR_POSITION())
            sys.stdout.flush()