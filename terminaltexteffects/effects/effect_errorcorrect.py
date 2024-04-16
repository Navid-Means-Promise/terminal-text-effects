import random
import typing
from collections.abc import Iterator
from dataclasses import dataclass

import terminaltexteffects.utils.arg_validators as arg_validators
from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import animation, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return ErrorCorrectEffect, EffectConfig


@argclass(
    name="errorcorrect",
    help="Some characters start in the wrong position and are corrected in sequence.",
    description="errorcorrect | Some characters start in the wrong position and are corrected in sequence.",
    epilog=f"""{arg_validators.EASING_EPILOG}
    
Example: terminaltexteffects errorcorrect --error-pairs 0.1 --swap-delay 10 --error-color e74c3c --correct-color 45bf55 --final-gradient-stops 8A008A 00D1FF FFFFFF --final-gradient-steps 12 --movement-speed 0.5""",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configuration for the ErrorCorrect effect.

    Attributes:
        error_pairs (float): Percent of characters that are in the wrong position. This is a float between 0 and 1.0. 0.2 means 20 percent of the characters will be in the wrong position.
        swap_delay (int): Number of animation steps between swaps.
        error_color (graphics.Color): Color for the characters that are in the wrong position.
        correct_color (graphics.Color): Color for the characters once corrected, this is a gradient from error-color and fades to final-color.
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color.
        movement_speed (float): Speed of the characters while moving to the correct position. Note: Speed effects the number of steps in the easing function."""

    error_pairs: float = ArgField(
        cmd_name="--error-pairs",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.1,
        metavar="(int > 0)",
        help="Percent of characters that are in the wrong position. This is a float between 0 and 1.0. 0.2 means 20 percent of the characters will be in the wrong position.",
    )  # type: ignore[assignment]
    "float : Percent of characters that are in the wrong position. This is a float between 0 and 1.0. 0.2 means 20 percent of the characters will be in the wrong position."

    swap_delay: int = ArgField(
        cmd_name="--swap-delay",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=10,
        metavar="(int > 0)",
        help="Number of animation steps between swaps.",
    )  # type: ignore[assignment]
    "int : Number of animation steps between swaps."

    error_color: graphics.Color = ArgField(
        cmd_name=["--error-color"],
        type_parser=arg_validators.Color.type_parser,
        default="e74c3c",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters that are in the wrong position.",
    )  # type: ignore[assignment]
    "graphics.Color : Color for the characters that are in the wrong position."

    correct_color: graphics.Color = ArgField(
        cmd_name=["--correct-color"],
        type_parser=arg_validators.Color.type_parser,
        default="45bf55",
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Color for the characters once corrected, this is a gradient from error-color and fades to final-color.",
    )  # type: ignore[assignment]
    "graphics.Color : Color for the characters once corrected, this is a gradient from error-color and fades to final-color."

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("8A008A", "00D1FF", "FFFFFF"),
        metavar="(XTerm [0-255] OR RGB Hex [000000-ffffff])",
        help="Space separated, unquoted, list of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient (applied from bottom to top). If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        nargs="+",
        default=(12,),
        metavar="(int > 0)",
        help="Space separated, unquoted, list of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_direction: graphics.Gradient.Direction = ArgField(
        cmd_name="--final-gradient-direction",
        type_parser=arg_validators.GradientDirection.type_parser,
        default=graphics.Gradient.Direction.VERTICAL,
        metavar=arg_validators.GradientDirection.METAVAR,
        help="Direction of the gradient for the final color.",
    )  # type: ignore[assignment]
    "graphics.Gradient.Direction : Direction of the gradient for the final color."

    movement_speed: float = ArgField(
        cmd_name="--movement-speed",
        type_parser=arg_validators.PositiveFloat.type_parser,
        default=0.5,
        metavar="(float > 0)",
        help="Speed of the characters while moving to the correct position. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )  # type: ignore[assignment]
    "float : Speed of the characters while moving to the correct position. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect."

    @classmethod
    def get_effect_class(cls):
        return ErrorCorrectEffect


class ErrorCorrectEffect:
    """Effect that swaps characters from an incorrect initial position to the correct position."""

    def __init__(
        self,
        input_data: str,
        effect_config: EffectConfig = EffectConfig(),
        terminal_config: TerminalConfig = TerminalConfig(),
    ):
        """Initializes the effect.

        Args:
            input_data (str): The input data to apply the effect to.
            effect_config (EffectConfig): The configuration for the effect.
            terminal_config (TerminalConfig): The configuration for the terminal.
        """
        self.terminal = Terminal(input_data, terminal_config)
        self.config = effect_config
        self._built = False
        self._pending_chars: list[EffectCharacter] = []
        self._active_chars: list[EffectCharacter] = []
        self._swapped: list[tuple[EffectCharacter, EffectCharacter]] = []
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def build(self) -> None:
        """Prepares the data for the effect by swapping positions and generating animations and waypoints."""
        self._pending_chars.clear()
        self._active_chars.clear()
        self._swapped.clear()
        self._character_final_color_map.clear()
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
        for character in self.terminal.get_characters():
            spawn_scene = character.animation.new_scene()
            spawn_scene.add_frame(character.input_symbol, 1, color=self._character_final_color_map[character])
            character.animation.activate_scene(spawn_scene)
            self.terminal.set_character_visibility(character, True)
        all_characters: list[EffectCharacter] = list(self.terminal._input_characters)
        correcting_gradient = graphics.Gradient(self.config.error_color, self.config.correct_color, steps=10)
        block_symbol = "▓"
        block_wipe_start = ("▁", "▂", "▃", "▄", "▅", "▆", "▇", "█")
        block_wipe_end = ("▇", "▆", "▅", "▄", "▃", "▂", "▁")
        for _ in range(int(self.config.error_pairs * len(self.terminal.get_characters()))):
            if len(all_characters) < 2:
                break
            char1 = all_characters.pop(random.randrange(len(all_characters)))
            char2 = all_characters.pop(random.randrange(len(all_characters)))
            char1.motion.set_coordinate(char2.input_coord)
            char1_input_coord_path = char1.motion.new_path(id="input_coord", speed=self.config.movement_speed)
            char1_input_coord_path.new_waypoint(char1.input_coord)
            char2.motion.set_coordinate(char1.input_coord)
            char2_input_coord_path = char2.motion.new_path(id="input_coord", speed=self.config.movement_speed)
            char2_input_coord_path.new_waypoint(char2.input_coord)
            self._swapped.append((char1, char2))
            for character in (char1, char2):
                first_block_wipe = character.animation.new_scene()
                last_block_wipe = character.animation.new_scene()
                for block in block_wipe_start:
                    first_block_wipe.add_frame(block, 3, color=self.config.error_color)
                for block in block_wipe_end:
                    last_block_wipe.add_frame(block, 3, color=self.config.correct_color)
                initial_scene = character.animation.new_scene()
                initial_scene.add_frame(character.input_symbol, 1, color=self.config.error_color)
                character.animation.activate_scene(initial_scene)
                error_scene = character.animation.new_scene(id="error")
                for _ in range(10):
                    error_scene.add_frame(block_symbol, 3, color=self.config.error_color)
                    error_scene.add_frame(character.input_symbol, 3, color="ffffff")
                correcting_scene = character.animation.new_scene(sync=animation.SyncMetric.DISTANCE)
                correcting_scene.apply_gradient_to_symbols(correcting_gradient, "█", 3)
                final_scene = character.animation.new_scene()
                char_final_gradient = graphics.Gradient(
                    self.config.correct_color, self._character_final_color_map[character], steps=10
                )
                final_scene.apply_gradient_to_symbols(char_final_gradient, character.input_symbol, 3)
                input_coord_path = character.motion.query_path("input_coord")
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    error_scene,
                    EventHandler.Action.ACTIVATE_SCENE,
                    first_block_wipe,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    first_block_wipe,
                    EventHandler.Action.ACTIVATE_SCENE,
                    correcting_scene,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    first_block_wipe,
                    EventHandler.Action.ACTIVATE_PATH,
                    input_coord_path,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_ACTIVATED,
                    input_coord_path,
                    EventHandler.Action.SET_LAYER,
                    1,
                )
                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    input_coord_path,
                    EventHandler.Action.SET_LAYER,
                    0,
                )

                character.event_handler.register_event(
                    EventHandler.Event.PATH_COMPLETE,
                    input_coord_path,
                    EventHandler.Action.ACTIVATE_SCENE,
                    last_block_wipe,
                )
                character.event_handler.register_event(
                    EventHandler.Event.SCENE_COMPLETE,
                    last_block_wipe,
                    EventHandler.Action.ACTIVATE_SCENE,
                    final_scene,
                )
        self._built = True

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self._built:
            self.build()
        while self._swapped or self._active_chars:
            swap_delay = self.config.swap_delay
            if self._swapped:
                next_pair = self._swapped.pop(0)
                for char in next_pair:
                    char.animation.activate_scene(char.animation.query_scene("error"))
                    self._active_chars.append(char)
            while swap_delay:
                yield self.terminal.get_formatted_output_string()
                self._animate_chars()

                self._active_chars = [character for character in self._active_chars if character.is_active]
                if not self._active_chars:
                    pass
                swap_delay -= 1
        yield self.terminal.get_formatted_output_string()
        self._built = False

    def _animate_chars(self) -> None:
        """Animates the characters by calling the tick method on all active characters."""
        for character in self._active_chars:
            character.tick()
