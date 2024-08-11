# Define the base name for your files
base_name = "tunar-nihavend-taksim"
BASE_DIR = "input"
BASE_NAME = f"{BASE_DIR}/{base_name}"


rule crepe:
    input:
        wav=BASE_NAME + ".wav",
    output:
        csv=BASE_NAME + ".f0.csv",
    shell:
        "crepe {input.wav} -c full -V"


rule record_cli:
    input:
        script="source/main.py",
        args=BASE_NAME + ".f0.csv",
        audio=BASE_NAME + ".wav",  # Path to the .wav file
    output:
        mp4=BASE_NAME + ".mp4",
    shell:
        "python record_cli.py {input.script} {output.mp4} {input.args} {input.audio}"


rule run_render_via_pygame:
    input:
        script="source/main.py",
        loudness_csv=BASE_NAME + ".f0.csv",
        audio=BASE_NAME + ".wav",
    shell:
        "python {input.script} {input.loudness_csv} {input.audio}"
