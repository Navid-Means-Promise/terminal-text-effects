import typing
from collections.abc import Iterator
from dataclasses import dataclass

from terminaltexteffects.base_character import EffectCharacter, EventHandler
from terminaltexteffects.utils import arg_validators, easing, graphics
from terminaltexteffects.utils.argsdataclass import ArgField, ArgsDataClass, argclass
from terminaltexteffects.utils.geometry import Coord
from terminaltexteffects.utils.terminal import Terminal, TerminalConfig


def get_effect_and_args() -> tuple[type[typing.Any], type[ArgsDataClass]]:
    return ScatteredEffect, EffectConfig


@argclass(
    name="scattered",
    help="Move the characters into place from random starting locations.",
    description="scattered | Move the characters into place from random starting locations.",
    epilog=f"""{arg_validators.EASING_EPILOG}
Example: terminaltexteffects scattered --final-gradient-stops ff9048 ab9dff bdffea --final-gradient-steps 12 --final-gradient-frames 12 --movement-speed 0.5 --movement-easing IN_OUT_BACK""",
)
@dataclass
class EffectConfig(ArgsDataClass):
    """Configuration for the effect.

    Attributes:
        final_gradient_stops (tuple[graphics.Color, ...]): Tuple of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.
        final_gradient_steps (tuple[int, ...]): Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation.
        final_gradient_frames (int): Number of frames to display each gradient step.
        final_gradient_direction (graphics.Gradient.Direction): Direction of the gradient for the final color.
        movement_speed (float): Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.
        movement_easing (easing.EasingFunction): Easing function to use for character movement."""

    final_gradient_stops: tuple[graphics.Color, ...] = ArgField(
        cmd_name=["--final-gradient-stops"],
        type_parser=arg_validators.Color.type_parser,
        nargs="+",
        default=("ff9048", "ab9dff", "bdffea"),
        metavar=arg_validators.Color.METAVAR,
        help="Space separated, unquoted, list of colors for the character gradient. If only one color is provided, the characters will be displayed in that color.",
    )  # type: ignore[assignment]
    "tuple[graphics.Color, ...] : Tuple of colors for the character gradient. If only one color is provided, the characters will be displayed in that color."

    final_gradient_steps: tuple[int, ...] = ArgField(
        cmd_name="--final-gradient-steps",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=(12,),
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of gradient steps to use. More steps will create a smoother and longer gradient animation.",
    )  # type: ignore[assignment]
    "tuple[int, ...] : Tuple of the number of gradient steps to use. More steps will create a smoother and longer gradient animation."

    final_gradient_frames: int = ArgField(
        cmd_name="--final-gradient-frames",
        type_parser=arg_validators.PositiveInt.type_parser,
        default=12,
        metavar=arg_validators.PositiveInt.METAVAR,
        help="Number of frames to display each gradient step.",
    )  # type: ignore[assignment]
    "int : Number of frames to display each gradient step."

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
        metavar=arg_validators.PositiveFloat.METAVAR,
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )  # type: ignore[assignment]
    "float : Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect."

    movement_easing: easing.EasingFunction = ArgField(
        cmd_name="--movement-easing",
        default=easing.in_out_back,
        type_parser=arg_validators.Ease.type_parser,
        help="Easing function to use for character movement.",
    )  # type: ignore[assignment]
    "easing.EasingFunction : Easing function to use for character movement."

    @classmethod
    def get_effect_class(cls):
        return ScatteredEffect


class ScatteredEffect:
    """Effect that moves the characters into position from random starting locations."""

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
        self._character_final_color_map: dict[EffectCharacter, graphics.Color] = {}

    def build(self) -> None:
        """Prepares the data for the effect by scattering the characters within range of the input width and height."""
        self._pending_chars.clear()
        self._active_chars.clear()
        self._character_final_color_map.clear()
        final_gradient = graphics.Gradient(*self.config.final_gradient_stops, steps=self.config.final_gradient_steps)
        final_gradient_mapping = final_gradient.build_coordinate_color_mapping(
            self.terminal.output_area.top, self.terminal.output_area.right, self.config.final_gradient_direction
        )
        for character in self.terminal.get_characters():
            self._character_final_color_map[character] = final_gradient_mapping[character.input_coord]
            if self.terminal.output_area.right < 2 or self.terminal.output_area.top < 2:
                character.motion.set_coordinate(Coord(1, 1))
            else:
                character.motion.set_coordinate(self.terminal.output_area.random_coord())
            input_coord_path = character.motion.new_path(
                speed=self.config.movement_speed, ease=self.config.movement_easing
            )
            input_coord_path.new_waypoint(character.input_coord)
            character.event_handler.register_event(
                EventHandler.Event.PATH_ACTIVATED, input_coord_path, EventHandler.Action.SET_LAYER, 1
            )
            character.event_handler.register_event(
                EventHandler.Event.PATH_COMPLETE, input_coord_path, EventHandler.Action.SET_LAYER, 0
            )
            character.motion.activate_path(input_coord_path)
            self.terminal.set_character_visibility(character, True)
            gradient_scn = character.animation.new_scene()
            char_gradient = graphics.Gradient(
                final_gradient.spectrum[0], self._character_final_color_map[character], steps=10
            )
            gradient_scn.apply_gradient_to_symbols(
                char_gradient, character.input_symbol, self.config.final_gradient_frames
            )
            character.animation.activate_scene(gradient_scn)
            self._active_chars.append(character)
        self._built = True

    @property
    def built(self) -> bool:
        """Returns True if the effect has been built."""
        return self._built

    def __iter__(self) -> Iterator[str]:
        """Runs the effect."""
        if not self._built:
            self.build()
        yield self.terminal.get_formatted_output_string()
        while self._pending_chars or self._active_chars:
            self._animate_chars()
            self._active_chars = [character for character in self._active_chars if character.is_active]
            yield self.terminal.get_formatted_output_string()
        self._built = False

    def _animate_chars(self) -> None:
        for character in self._active_chars:
            character.tick()
