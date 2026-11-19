"""Account for dock panels when fitting the existing toolbar to the screen."""
def reserved_dock_width(window):
    getter = getattr(window, "centralWidget", None)
    central = getter() if getter else None
    if central is None:
        return 0
    return max(0, window.width()-central.width())
