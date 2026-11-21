#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Рисует apple-touch-icon.png (иконка «На экран Домой») без сторонних библиотек:
собственный PNG-энкодер + 4x суперсэмплинг для сглаживания.

Запуск:  python3 make_icon.py
"""

import struct
import zlib
import os

W = H = 152          # размер иконки iPad (iOS 9)
SS = 4               # суперсэмплинг

FONT = {
    '0': ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    '1': ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    '2': ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    '3': ["11111", "00010", "00100", "00010", "00001", "10001", "01110"],
    '4': ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    '5': ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    '6': ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    '7': ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    '8': ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    '9': ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
}

# --- палитра ---
BG      = (11, 11, 11)      # фон иконки
CARD    = (24, 24, 24)      # карточка
DIGIT   = (232, 232, 232)   # цифра
FOLD    = (0, 0, 0)         # линия сгиба


def rounded(x, y, x0, y0, x1, y1, r):
    """True, если точка внутри скруглённого прямоугольника."""
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        dx = abs(x - cx)
        dy = abs(y - cy)
        in_x = (x < cx and x0 <= x <= x0 + r) or (x > cx and x1 - r <= x <= x1)
        in_y = (y < cy and y0 <= y <= y0 + r) or (y > cy and y1 - r <= y <= y1)
        if in_x and in_y and (dx * dx + dy * dy) > r * r:
            return False
    return True


def digit_pixel(gx, gy, ch, cell, ox, oy):
    """Покрытость (0..1) пикселя подложки глифом в суперсэмпле."""
    rows = FONT[ch]
    hit = 0
    total = 0
    for sy in range(SS):
        for sx in range(SS):
            px = gx + (sx + 0.5) / SS
            py = gy + (sy + 0.5) / SS
            total += 1
            cx = int((px - ox) / cell)
            cy = int((py - oy) / cell)
            if 0 <= cx < 5 and 0 <= cy < 7 and rows[cy][cx] == '1':
                hit += 1
    return hit / total


def main():
    out = os.path.dirname(os.path.abspath(__file__))
    text = "21"

    # --- геометрия карточек ---
    card_w, card_h, gap = 44, 70, 8
    total_w = card_w * 2 + gap
    x_left = (W - total_w) // 2
    y_top = (H - card_h) // 2
    cards = [(x_left, y_top), (x_left + card_w + gap, y_top)]

    # --- геометрия глифов ---
    cell = 6                       # px на "пиксель" шрифта
    glyph_w, glyph_h = 5 * cell, 7 * cell
    buf = [[BG for _ in range(W)] for _ in range(H)]

    for i, (cx, cy) in enumerate(cards):
        for y in range(H):
            for x in range(W):
                if rounded(x, y, cx, cy, cx + card_w - 1, cy + card_h - 1, 7):
                    buf[y][x] = CARD

    # глифы
    for i, (cx, cy) in enumerate(cards):
        ch = text[i]
        gx = cx + (card_w - glyph_w) / 2.0
        gy = cy + (card_h - glyph_h) / 2.0
        for y in range(int(gy) - 1, int(gy + glyph_h) + 2):
            for x in range(int(gx) - 1, int(gx + glyph_w) + 2):
                if not (0 <= x < W and 0 <= y < H):
                    continue
                a = digit_pixel(x, y, ch, cell, gx, gy)
                if a <= 0:
                    continue
                base = buf[y][x]
                buf[y][x] = tuple(int(round(base[k] * (1 - a) + DIGIT[k] * a)) for k in range(3))

    # линия сгиба по центру каждой карточки
    fold_y = y_top + card_h // 2
    for i, (cx, cy) in enumerate(cards):
        for y in (fold_y, fold_y + 1):
            for x in range(cx + 1, cx + card_w - 1):
                if 0 <= y < H:
                    buf[y][x] = FOLD

    # лёгкое затемнение нижней половины карточки
    for i, (cx, cy) in enumerate(cards):
        for y in range(fold_y + 2, cy + card_h):
            k = (y - fold_y) / float(card_h)
            for x in range(cx + 1, cx + card_w - 1):
                c = buf[y][x]
                buf[y][x] = tuple(max(0, int(v * (1 - 0.22 * k))) for v in c)

    # --- кодирование PNG ---
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter type: None
        for x in range(W):
            raw += bytes(buf[y][x])

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n" +
           chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)) +
           chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
           chunk(b"IEND", b""))

    path = os.path.join(out, "apple-touch-icon.png")
    with open(path, "wb") as f:
        f.write(png)
    print("written:", path, len(png), "bytes")


if __name__ == "__main__":
    main()
