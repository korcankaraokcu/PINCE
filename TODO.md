
---
**2022/11/24 -- Fix scrolling via the vertical scrollbar in memoryview**

[fixed] + Currently using the vertical scrollbar to scroll the disassembled instructions in the memoryview, and in hex view, results in endless movement of the scrollbar but no actual scrolling takes place.

---

---
**2022/11/24 -- Hex and Ascii Models in Memory View Don't show the proper values**

[fixed] + Currently the Hex and Ascii Viewer are showing black squares, or <?>, it should
  show the hex value (in the hex view) and the Ascii value (or a . for non-ascii).

[fixed] + Additionally, the hex digits are not showing two digits per entry (eg 12 34, instead of 1 3)

[fixed] + Ascii text-view has <?> for non-printable characters, this needs to be changed to .

[fixed] + Pressing PgUp/Dn, or arrow keys does not scroll the hex view (but the mouse wheel does)

---
