import argparse
import random

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import easing, graphics
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "binarypath",
        formatter_class=argtypes.CustomFormatter,
        help="Binary representations of each character move through the terminal towards the home coordinate of the character.",
        description="Binary representations of each character move through the terminal towards the home coordinate of the character.",
        epilog="""Example: effect_example""",
    )
    effect_parser.set_defaults(effect_class=BinaryPathEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Minimum time, in seconds, between animation steps. This value does not normally need to be modified. Use this to increase the playback speed of all aspects of the effect. This will have no impact beyond a certain lower threshold due to the processing speed of your device.",
    )
    effect_parser.add_argument(
        "--base-color",
        type=argtypes.color,
        default="265e3c",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters when the binary group combines in place.",
    )
    effect_parser.add_argument(
        "--binary-colors",
        type=argtypes.color,
        nargs="*",
        default=["044E29", "157e38", "45bf55", "95ed87"],
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the binary characters. Character color is randomly assigned from this list.",
    )
    effect_parser.add_argument(
        "--final-color",
        type=argtypes.color,
        default="45bf55",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters after the final gradient wipe.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.positive_float,
        default=1.0,
        metavar="(float > 0)",
        help="Speed of the binary groups as they travel around the terminal.",
    )
    effect_parser.add_argument(
        "--active-binary-groups",
        type=argtypes.float_zero_to_one,
        default=0.05,
        metavar="(float 0 < n <= 1)",
        help="Maximum number of binary groups that are active at any given time. Lower this to improve performance.",
    )
    effect_parser.add_argument(
        "--skip-final-wipe",
        action="store_true",
        default=False,
        help="Skip the final gradient wipe. This will result in the characters remaining as base-color.",
    )


class BinaryRepresentation:
    def __init__(self, character: EffectCharacter, terminal: Terminal):
        self.character = character
        self.terminal = terminal
        self.binary_string = format(ord(self.character.symbol), "08b")
        self.binary_characters: list[EffectCharacter] = []
        self.pending_binary_characters: list[EffectCharacter] = []
        self.input_coord = self.character.input_coord
        self.is_active = False

    def travel_complete(self) -> bool:
        """Determines if the binary representation has completed its travel, meaning all binary characters have reached their input coordinate.

        Returns:
            bool: True if the binary representation has completed its travel, False otherwise.
        """
        return all(bin_char.motion.current_coord == self.input_coord for bin_char in self.binary_characters)

    def deactivate(self) -> None:
        """Deactivates the binary representation by deactivating all binary characters."""
        for bin_char in self.binary_characters:
            self.terminal.set_character_visibility(bin_char, False)
        self.is_active = False

    def activate_source_character(self) -> None:
        """Activates the source character of the binary representation."""
        self.terminal.set_character_visibility(self.character, True)
        self.character.animation.activate_scene(self.character.animation.query_scene("collapse_scn"))


class BinaryPathEffect:
    """Effect that decodes characters into their binary form. Characters travel from outside the output area towards their input coordinate,
    moving at right angles."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.pending_binary_representations: list[BinaryRepresentation] = []

    def prepare_data(self) -> None:
        complete_gradient = graphics.Gradient(["ffffff", self.args.base_color], 10)
        brighten_gradient = graphics.Gradient([self.args.base_color, "ffffff", self.args.final_color], 25)
        for character in self.terminal._input_characters:
            bin_rep = BinaryRepresentation(character, self.terminal)
            for binary_char in bin_rep.binary_string:
                bin_rep.binary_characters.append(self.terminal.add_character(binary_char, Coord(0, 0)))
                bin_rep.pending_binary_characters.append(bin_rep.binary_characters[-1])
            self.pending_binary_representations.append(bin_rep)

        for bin_rep in self.pending_binary_representations:
            path_coords: list[Coord] = []
            starting_coord = self.terminal.output_area.random_coord(outside_scope=True)
            path_coords.append(starting_coord)
            last_orientation = random.choice(("col", "row"))
            while path_coords[-1] != bin_rep.character.input_coord:
                last_coord = path_coords[-1]
                if last_coord.column > bin_rep.character.input_coord.column:
                    column_direction = -1
                elif last_coord.column == bin_rep.character.input_coord.column:
                    column_direction = 0
                else:
                    column_direction = 1
                if last_coord.row > bin_rep.character.input_coord.row:
                    row_direction = -1
                elif last_coord.row == bin_rep.character.input_coord.row:
                    row_direction = 0
                else:
                    row_direction = 1
                max_column_distance = abs(last_coord.column - bin_rep.character.input_coord.column)
                max_row_distance = abs(last_coord.row - bin_rep.character.input_coord.row)
                if last_orientation == "col" and max_row_distance > 0:
                    next_coord = Coord(
                        last_coord.column,
                        last_coord.row
                        + (
                            random.randint(1, min(max_row_distance, max(10, int(self.terminal.input_width * 0.2))))
                            * row_direction
                        ),
                    )
                    last_orientation = "row"
                elif last_orientation == "row" and max_column_distance > 0:
                    next_coord = Coord(
                        last_coord.column + (random.randint(1, min(max_column_distance, 4)) * column_direction),
                        last_coord.row,
                    )
                    last_orientation = "col"
                else:
                    next_coord = bin_rep.character.input_coord

                path_coords.append(next_coord)

            path_coords.append(next_coord)
            final_coord = bin_rep.character.input_coord
            path_coords.append(final_coord)
            for bin_effectchar in bin_rep.binary_characters:
                bin_effectchar.motion.set_coordinate(path_coords[0])
                digital_path = bin_effectchar.motion.new_path(speed=self.args.movement_speed)
                for coord in path_coords:
                    digital_path.new_waypoint(coord)
                bin_effectchar.motion.activate_path(digital_path)
                bin_effectchar.layer = 1
                color_scn = bin_effectchar.animation.new_scene()
                color_scn.add_frame(bin_effectchar.symbol, 1, color=random.choice(self.args.binary_colors))
                bin_effectchar.animation.activate_scene(color_scn)

        for character in self.terminal._input_characters:
            collapse_scn = character.animation.new_scene(ease=easing.in_quad, id="collapse_scn")
            for spectrum in complete_gradient.spectrum:
                collapse_scn.add_frame(character.input_symbol, 10, color=spectrum)

            brighten_scn = character.animation.new_scene(id="brighten_scn")
            for spectrum in brighten_gradient.spectrum:
                brighten_scn.add_frame(character.input_symbol, 2, color=spectrum)
            brighten_scn.add_frame(character.input_symbol, 2, color=self.args.final_color)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        active_binary_reps: list[BinaryRepresentation] = []
        complete = False
        phase = "travel"
        final_wipe_chars = self.terminal.get_characters_grouped(
            grouping=self.terminal.CharacterGroup.DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT
        )
        max_active_binary_groups = max(
            1, int(self.args.active_binary_groups * len(self.pending_binary_representations))
        )
        while not complete or self.active_chars:
            if phase == "travel":
                while len(active_binary_reps) < max_active_binary_groups and self.pending_binary_representations:
                    next_binary_rep = self.pending_binary_representations.pop(
                        random.randrange(len(self.pending_binary_representations))
                    )
                    next_binary_rep.is_active = True
                    active_binary_reps.append(next_binary_rep)

                if active_binary_reps:
                    for active_rep in active_binary_reps:
                        if active_rep.pending_binary_characters:
                            next_char = active_rep.pending_binary_characters.pop(0)
                            self.active_chars.append(next_char)
                            self.terminal.set_character_visibility(next_char, True)
                        elif active_rep.travel_complete():
                            active_rep.deactivate()
                            active_rep.activate_source_character()
                            self.active_chars.append(active_rep.character)

                    active_binary_reps = [binary_rep for binary_rep in active_binary_reps if binary_rep.is_active]

                if not self.active_chars:
                    phase = "wipe"

            if phase == "wipe":
                if final_wipe_chars and not self.args.skip_final_wipe:
                    next_group = final_wipe_chars.pop(0)
                    for character in next_group:
                        character.animation.activate_scene(character.animation.query_scene("brighten_scn"))
                        self.terminal.set_character_visibility(character, True)
                        self.active_chars.append(character)
                else:
                    complete = True
            self.terminal.print()
            self.animate_chars()

            self.active_chars = [character for character in self.active_chars if character.is_active]
        self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self.active_chars:
            character.tick()
