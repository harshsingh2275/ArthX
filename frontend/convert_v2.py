import re
import json

with open('d:/ArthX/frontend/stitch-landing-export/code.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Extract tailwind config
config_match = re.search(r'<script id="tailwind-config">tailwind\.config=({.*?})</script>', html, re.DOTALL)
if config_match:
    config_json = config_match.group(1)
    
    tailwind_js = f"""/** @type {{import('tailwindcss').Config}} */
export default {{
  content: [
    "./index.html",
    "./src/**/*.{{js,ts,jsx,tsx}}",
  ],
  darkMode: "class",
  theme: {config_json}.theme,
  plugins: [],
}}
"""
    with open('d:/ArthX/frontend/tailwind.config.js', 'w', encoding='utf-8') as f:
        f.write(tailwind_js)

# Extract body
body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
body = body_match.group(1) if body_match else html

# Convert class to className
body = re.sub(r'\bclass=', 'className=', body)
# Convert for to htmlFor
body = re.sub(r'\bfor=', 'htmlFor=', body)

# Fix empty tags (only if not already closed)
body = re.sub(r'<img([^>]*?)(?<!/)>', r'<img\1/>', body)
body = re.sub(r'<br([^>]*?)(?<!/)>', r'<br\1/>', body)
body = re.sub(r'<hr([^>]*?)(?<!/)>', r'<hr\1/>', body)
body = re.sub(r'<input([^>]*?)(?<!/)>', r'<input\1/>', body)

# Fix comments
body = re.sub(r'<!--(.*?)-->', r'{/* \1 */}', body, flags=re.DOTALL)

# Keep the Exact HTML without replacing any colors!

# Fix routing just for the demo button since we need it
body = body.replace('href="#" data-path="demo"', 'href="/app"')
body = body.replace('href="https://github.com"', 'href="https://github.com/harshsingh2275/ArthX"')

# Create JSX component
jsx_content = f"""import React from 'react';
import {{ Link }} from 'react-router-dom';

export default function LandingPage() {{
  return (
    <div className="bg-surface font-body-md text-on-surface antialiased">
      {body}
    </div>
  );
}}
"""

# Replace href="/app" with <Link>
jsx_content = re.sub(r'<a([^>]+)href="/app"([^>]*)>(.*?)</a>', r'<Link\1to="/app"\2>\3</Link>', jsx_content, flags=re.DOTALL)

with open('d:/ArthX/frontend/src/pages/LandingPage.jsx', 'w', encoding='utf-8') as f:
    f.write(jsx_content)

print('Successfully generated LandingPage.jsx and tailwind.config.js')
