"""
A MicroPython module for handling 
debounced button presses using interrupts.

https://github.com/evgenii-d/micropython-simple-button
"""

# pylint: disable=E0401:import-error
from machine import Pin                 # type: ignore
from utime import ticks_ms, ticks_diff  # type: ignore


class SimpleButton:
    """
    Handles a button connected to a GPIO pin, 
    providing debouncing via interrupts.
    Manages press/release callbacks and supports active-low/high
    circuits with internal or external pull resistors.
    """

    # pylint: disable-next=R0913:too-many-arguments
    def __init__(
        self,
        pin: int,
        *,
        press_callback=None,    # Optional[Callable[[], None]]
        release_callback=None,  # Optional[Callable[[], None]]
        debounce_ms: int = 50,
        pull: int | None = Pin.PULL_UP,
        active_low: bool = True
    ):
        """Initialize the Button.

        Args:
            pin (int): 
                GPIO pin number for the button.
            press_callback (Callable, optional): 
                Function to call on button press. Defaults to None.
            release_callback (Callable, optional): 
                Function to call on button release. Defaults to None.
            debounce_ms (int, optional): 
                Debounce time in milliseconds. Defaults to 50.
            pull (int | None, optional): 
                Pin.PULL_UP, Pin.PULL_DOWN, or None 
                (for external resistors). Defaults to Pin.PULL_UP.
            active_low (bool, optional): 
                True if low signal means pressed (pull-up),
                False if high signal means pressed (pull-down).
                Defaults to True.
        """
        # Basic input validation
        if pull is not None and pull not in (Pin.PULL_UP, Pin.PULL_DOWN):
            raise ValueError(
                "pull must be Pin.PULL_UP, Pin.PULL_DOWN or None"
            )
        if not isinstance(debounce_ms, int) or debounce_ms < 0:
            raise ValueError("debounce_ms must be a non-negative int")

        self._pin = Pin(pin, Pin.IN, pull)
        self._press_callback = press_callback
        self._release_callback = release_callback
        self._debounce_ms = debounce_ms
        self._last_time = 0  # Time of last confirmed change
        self._active_low = active_low

        # Read the pin's initial physical state
        # to set the starting logical state.
        initial_physical_state = self._pin.value()
        if self._active_low:
            # If active_low, logical state (0=pressed) matches physical state.
            self._state = initial_physical_state
        else:
            # If active_high, logical state is the inverse of physical state.
            self._state = not initial_physical_state

        # Set up interrupts for both falling and rising edges.
        self._pin.irq(
            trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING,
            handler=self._irq_handler
        )

    # pylint: disable-next=W0613:unused-argument
    def _irq_handler(self, pin: Pin) -> None:
        """IRQ handler called on pin changes. Handles debouncing."""
        now = ticks_ms()

        # Basic debounce:
        # Has enough time passed since the last confirmed change?
        if ticks_diff(now, self._last_time) < self._debounce_ms:
            # Not enough time passed, ignore as potential bounce.
            return

        # Read the raw physical signal now that debounce time has passed.
        physical_state = self._pin.value()
        # Determine the logical state (0=pressed, 1=released) based on config.
        if self._active_low:
            logical_state = physical_state
        else:
            logical_state = not physical_state

        if logical_state != self._state:
            # Confirmed state change
            self._last_time = now  # Record the time of this stable change.
            self._state = logical_state  # Update the official button state.

            # Call the appropriate callback based on the new stable state.
            if self._state == 0:
                # Pressed
                if self._press_callback:
                    self._press_callback()
            else:
                # Released
                if self._release_callback:
                    self._release_callback()

    def is_pressed(self) -> bool:
        """
        Checks if the button is currently considered pressed.
        Returns the debounced state.
        """
        return self._state == 0

    def is_released(self) -> bool:
        """
        Checks if the button is currently considered released.
        Returns the debounced state.
        """
        return self._state == 1

    def deinit(self) -> None:
        """Disables the interrupt handler for this button."""
        self._pin.irq(handler=None)
