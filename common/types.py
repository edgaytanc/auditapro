from typing import Literal, NoReturn, Optional, TypedDict, List

from users.types import ROLES

NavBarLinkType = Literal["anchor", "collapse"]


class NavBarLink(TypedDict):
    type: NavBarLinkType
    url: str
    name: str
    active: bool
    icon: str
    collapse_values: Optional[List["CollapseNavBarLink"]]
    hide_to: Optional[List[ROLES]]


class CollapseNavBarLink(TypedDict):
    type: NavBarLinkType
    url: str
    name: str
    active: bool
    icon: NoReturn
    collapse_values: NoReturn
    hide_to: Optional[List[ROLES]]
