# Define the base name for your files
base_name = "tunar-nihavend-taksim"
BASE_DIR = "input"
BASE_NAME = f"{BASE_DIR}/{base_name}"

rule record_cli:
    input:
        script="source/main.py",
        audio=BASE_NAME + ".wav",  # Path to the .wav file
    output:
        mp4=BASE_NAME + ".mp4",
    shell:
        "python record_cli.py {input.script} {output.mp4} {input.audio}"

rule run_render_via_pygame:
    input:
        script="source/main.py",
        audio=BASE_NAME + ".wav",
    shell:
        "python {input.script} {input.audio}"
