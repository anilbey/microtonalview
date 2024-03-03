# Define the base name for your files
base_name = "aka-saba-taksim"
BASE_DIR = "input"
BASE_NAME = f"{BASE_DIR}/{base_name}"


rule crepe:
    input:
        wav=BASE_NAME + ".wav",
    output:
        csv=BASE_NAME + ".f0.csv",
    shell:
        "crepe {input.wav} -c full -V"


rule append_loudness:
    input:
        wav=BASE_NAME + ".wav",
        f0_csv=BASE_NAME + ".f0.csv",
    output:
        loudness_csv=BASE_NAME + "-loudness.csv",
    shell:
        "python append_loudness.py {input.wav} {input.f0_csv} {output.loudness_csv}"


rule record_cli:
    input:
        script="visualiser/view.py",
        args=BASE_NAME + "-loudness.csv",  # loudness CSV file used as input to render-via-pygame.py
        audio=BASE_NAME + ".wav",  # Path to the .wav file
    output:
        mp4=BASE_NAME + ".mp4",
    shell:
        "python record_cli.py {input.script} {output.mp4} {input.args} {input.audio}"


rule run_render_via_pygame:
    input:
        script="visualiser/view.py",
        loudness_csv=BASE_NAME + "-loudness.csv",
        audio=BASE_NAME + ".wav",
    shell:
        "python {input.script} {input.loudness_csv} {input.audio}"
