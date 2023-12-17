# Define the base name for your files
BASE_NAME = "aka-saba-taksim"

rule all:
    input:
        BASE_NAME + ".mp4"

rule crepe:
    input:
        wav=BASE_NAME + ".wav"
    output:
        csv=BASE_NAME + ".f0.csv"
    shell:
        "crepe {input.wav} -c full -V"

rule append_loudness:
    input:
        wav=BASE_NAME + ".wav",
        f0_csv=BASE_NAME + ".f0.csv"
    output:
        loudness_csv=BASE_NAME + "-loudness.csv"
    shell:
        "python append_loudness.py {input.wav} {input.f0_csv} {output.loudness_csv}"

rule record_cli:
    input:
        script="render-via-pygame.py",
        args=BASE_NAME + "-loudness.csv",  # loudness CSV file used as input to render-via-pygame.py
        audio=BASE_NAME + ".wav"  # Path to the .wav file
    output:
        mp4=BASE_NAME + ".mp4"
    shell:
        "python record_cli.py {input.script} {output.mp4} {input.args} {input.audio}"
