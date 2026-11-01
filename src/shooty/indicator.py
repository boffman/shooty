"""Optional Ayatana AppIndicator menu for a resident capture helper."""


def install_indicator(application, gtk):
    """Install Capture and Quit actions; import optional bindings on demand."""
    import gi
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3, Gtk

    indicator = AyatanaAppIndicator3.Indicator.new(
        "shooty", "org.shooty.Shooty", AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS
    )
    indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
    menu = Gtk.Menu()
    capture = Gtk.MenuItem(label="Capture")
    capture.connect("activate", lambda *_: application._start_capture())
    menu.append(capture)
    quit_item = Gtk.MenuItem(label="Quit")
    quit_item.connect("activate", lambda *_: application.quit())
    menu.append(quit_item)
    menu.show_all()
    indicator.set_menu(menu)
    # The indicator is not a Gtk.Window; hold the application alive while it
    # owns the top-bar menu.
    application.hold()
    return indicator
