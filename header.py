import streamlit.components.v1 as components

def animated_text(text: str):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Text Animation</title>
      <style>
      @import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;800&display=swap");

      :root {{
        --clr-1: #00c2ff;
        --clr-2: #33ff8c;
        --clr-3: #ffc640;
        --clr-4: #e54cff;
        --fs: clamp(3rem, 8vw, 7rem);
        --ls: clamp(-1.75px, -0.25vw, -3.5px);
      }}

      body {{
        min-height: 100vh;
        display: grid;
        place-items: center;
        background-color: transparent;  /* Transparent background */
        font-family: "Inter", "DM Sans", Arial, sans-serif;
        margin: 0;
      }}

      .content {{
        text-align: center;
        background-color: transparent;  /* Ensure container is transparent */
      }}

      .title {{
        font-size: var(--fs);
        font-weight: 800;
        letter-spacing: var(--ls);
        position: relative;
        overflow: hidden;
        background: linear-gradient(90deg, var(--clr-1), var(--clr-2), var(--clr-3), var(--clr-4));
        background-size: 200%;
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        animation: animateText 5s linear infinite;
        margin: 0;
      }}

      @keyframes animateText {{
        0% {{
          background-position: 0%;
        }}
        100% {{
          background-position: 200%;
        }}
      }}
      </style>
    </head>
    <body>
      <div class="content">
        <h1 class="title">{text}</h1>
      </div>
    </body>
    </html>
    """

    # Return the HTML component with the animated text
    components.html(html_content, height=300, scrolling=False)
