"""Network configuration page object for static and DHCP updates."""

from __future__ import annotations

from typing import ClassVar

from web_shipment.pages.base_page import BasePage


class NetworkConfigurationPage(BasePage):
    """Drives the network interface configuration screen."""

    SELECTORS: ClassVar[dict[str, str]] = {
        # Confirmed live (DOM id dump, 2026-09-15) as a real el-select with options
        # oob_net0 / p0 / p1 - the form only ever edits whichever one is selected here.
        "interface_dropdown": "#interfaces",
        "ip_input": "#ipaddress",
        "netmask_input": "#netmask",
        "gateway_input": "#geteway",  # NOTE: real DOM id has this legacy typo - intentional, do not "fix"
        "mtu_input": "#mtu",
        "dhcp_toggle": "#dhcp",  # actually an el-checkbox, not a switch, but click() works the same
        "submit_button": "#networksubmit",
        "cancel_button": "#networkcancel",
        # NOTE (known gap): "#dns" is a real, editable DNS-server tag list (custom
        # component, not a plain el-input/el-select), confirmed live but not yet
        # automated - add a dedicated interaction method here if a test ever needs
        # to change DNS servers.
    }

    def select_interface(self, interface_name: str) -> None:
        """Select which interface (e.g. ``oob_net0``, ``p0``, ``p1``) subsequent calls edit.

        The form only ever acts on whichever interface is currently selected in the
        ``interface_dropdown``, so multi-interface flows must call this before filling
        in fields - it does not happen implicitly.
        """
        if self.page.locator(self.selectors["interface_dropdown"]).count() > 0:
            self.select_option("interface_dropdown", interface_name)

    def configure_static(
        self, ip_address: str, netmask: str = "255.255.255.0", interface_name: str | None = None
    ) -> None:
        """Apply a static IPv4 address/netmask, clearing optional gateway/MTU fields first.

        ``interface_name`` should be passed whenever more than one interface is in play
        (e.g. looping over the API's ``up_interfaces()``) - without it, the form silently
        edits whatever interface was last selected instead of the intended one.
        """
        if interface_name:
            self.select_interface(interface_name)

        self.fill("ip_input", ip_address)
        self.fill("netmask_input", netmask)

        if self.page.locator(self.selectors["gateway_input"]).count() > 0:
            self.fill("gateway_input", "")
        if self.page.locator(self.selectors["mtu_input"]).count() > 0:
            self.fill("mtu_input", "")

        self.click("submit_button")

    def enable_dhcp(self, interface_name: str | None = None) -> None:
        """Toggle DHCP on and submit the form for the given (or currently selected) interface."""
        if interface_name:
            self.select_interface(interface_name)

        self.click("dhcp_toggle")
        self.click("submit_button")
