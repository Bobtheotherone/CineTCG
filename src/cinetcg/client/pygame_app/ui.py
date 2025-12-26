from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame  # type: ignore[import-not-found]


Color = tuple[int, int, int]


def draw_text(
    screen: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    pos: tuple[int, int],
    color: Color = (240, 240, 240),
) -> None:
    img = font.render(text, True, color)
    screen.blit(img, pos)


@dataclass
class Button:
    rect: pygame.Rect
    text: str
    on_click: Callable[[], None]
    enabled: bool = True

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.on_click()
                return True
        return False

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        bg = (60, 60, 60) if self.enabled else (30, 30, 30)
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, width=2, border_radius=8)
        img = font.render(self.text, True, (240, 240, 240))
        r = img.get_rect(center=self.rect.center)
        screen.blit(img, r.topleft)


@dataclass
class Toggle:
    rect: pygame.Rect
    label: str
    value: bool
    on_change: Callable[[bool], None]

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.value = not self.value
                self.on_change(self.value)
                return True
        return False

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.rect(screen, (40, 40, 40), self.rect, border_radius=8)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, width=2, border_radius=8)
        box = pygame.Rect(self.rect.x + 10, self.rect.y + 10, 22, 22)
        pygame.draw.rect(screen, (220, 220, 220), box, width=2)
        if self.value:
            pygame.draw.line(screen, (220, 220, 220), (box.x + 4, box.y + 12), (box.x + 10, box.y + 18), 3)
            pygame.draw.line(screen, (220, 220, 220), (box.x + 10, box.y + 18), (box.x + 18, box.y + 6), 3)
        txt = font.render(self.label, True, (240, 240, 240))
        screen.blit(txt, (box.right + 10, self.rect.y + 8))


@dataclass
class TextInput:
    rect: pygame.Rect
    text: str
    on_submit: Callable[[str], None]
    active: bool = False
    max_len: int = 18

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        if not self.active:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.on_submit(self.text)
                self.active = False
                return True
            if event.key == pygame.K_ESCAPE:
                self.active = False
                return True
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return True
            if event.unicode and len(self.text) < self.max_len and event.unicode.isprintable():
                self.text += event.unicode
                return True
        return False

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        bg = (20, 20, 20) if self.active else (30, 30, 30)
        pygame.draw.rect(screen, bg, self.rect, border_radius=6)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, width=2, border_radius=6)
        img = font.render(self.text, True, (240, 240, 240))
        screen.blit(img, (self.rect.x + 8, self.rect.y + 6))
