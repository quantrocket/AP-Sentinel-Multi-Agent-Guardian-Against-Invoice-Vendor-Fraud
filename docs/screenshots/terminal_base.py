import cairosvg

def terminal_svg(title, lines, width=820, height=None, dot_colors=("#FF5F57","#FEBC2E","#28C840")):
    line_h = 20
    top_bar = 34
    pad_top = 14
    height = height or (top_bar + pad_top + line_h * len(lines) + 16)
    rows = []
    y = top_bar + pad_top + 14
    for text, color in lines:
        safe = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        rows.append(f'<text x="18" y="{y}" font-family="Menlo, Consolas, monospace" font-size="13" fill="{color}" xml:space="preserve">{safe}</text>')
        y += line_h
    dots = "".join(
        f'<circle cx="{18+i*18}" cy="{top_bar/2}" r="6" fill="{c}"/>' for i, c in enumerate(dot_colors)
    )
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="10" fill="#0D1117"/>
  <rect width="{width}" height="{top_bar}" rx="10" fill="#1B2430"/>
  <rect y="{top_bar-10}" width="{width}" height="10" fill="#1B2430"/>
  {dots}
  <text x="{width/2}" y="{top_bar/2+4}" text-anchor="middle" font-family="Arial" font-size="11" fill="#8B98A5">{safe_title}</text>
  {"".join(rows)}
</svg>'''
    return svg, height

def render(name, title, lines, width=820):
    svg, height = terminal_svg(title, lines, width)
    svg_path = f"/home/claude/ap-sentinel/docs/screenshots/{name}.svg"
    png_path = f"/home/claude/ap-sentinel/docs/screenshots/{name}.png"
    open(svg_path, "w").write(svg)
    cairosvg.svg2png(url=svg_path, write_to=png_path, output_width=width*2, output_height=height*2)
    print("rendered", png_path)
