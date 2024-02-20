mod audio_player;
mod fps;
use std::env;
use std::path::Path;

use audio_player::{AudioFile, AudioPlayerPlugin, AudioTimer};
use bevy::{
    prelude::*,
    window::{PresentMode, WindowTheme},
};
use bevy_prototype_lyon::prelude::*;
use fps::FPSPlugin;
use polars::{
    chunked_array::ops::ChunkAgg,
    frame::DataFrame,
    io::{csv::CsvReader, SerReader},
};

fn get_wav_duration<P: AsRef<Path>>(file_path: P) -> Result<f32, hound::Error> {
    let reader = hound::WavReader::open(file_path)?;
    let spec = reader.spec();
    let duration = reader.duration() as f32 / spec.sample_rate as f32;
    Ok(duration)
}


#[derive(Resource)]
struct DataFrameResource(DataFrame);

#[derive(Resource)]
struct AudioAnalysisData {
    min_frequency: f32,
    max_frequency: f32,
    min_loudness: f32,
    max_loudness: f32,
}

fn add_camera(mut commands: Commands) {
    commands.spawn(Camera2dBundle::default());
}

fn add_line(mut commands: Commands) {
    let line = shapes::Line(Vec2::new(0.0, -400.0), Vec2::new(0.0, 400.0)); // Adjust length as needed

    commands.spawn((
        ShapeBundle {
            path: GeometryBuilder::build_as(&line),
            ..default()
        },
        Fill::color(Color::CYAN),
        Stroke::new(
            Color::Rgba {
                red: (1.0),
                green: (0.6),
                blue: (0.2),
                alpha: (0.8),
            },
            1.0,
        ),
    ));
}

fn loudness_to_size(loudness: f32, min_loudness: f32, max_loudness: f32) -> f32 {
    let normalized_loudness = (loudness - min_loudness) / (max_loudness - min_loudness);
    let res = f32::max(1.0, normalized_loudness * 10.0); // Scale and ensure minimum size of 1
    res * 2.5 // Scale up to make circles bigger
}

fn filter_data_system(
    mut commands: Commands,
    mut audio_timer: ResMut<AudioTimer>,
    data_frame_resource: Res<DataFrameResource>,
    audio_analysis_data: Res<AudioAnalysisData>,
) {
    let current_time = audio_timer.0.elapsed_secs();
    // Check if 0.1 seconds have passed since the last process
    if current_time - audio_timer.1 < 0.1 {
        return;
    }
    // Update the last process time
    audio_timer.1 = current_time;

    // Filter the DataFrame based on current_time
    let mask = data_frame_resource
        .0
        .column("time")
        .unwrap()
        .f64()
        .unwrap()
        .into_iter()
        .map(|opt_t| {
            opt_t.map_or(false, |t| {
                let t_f32 = t as f32;  
                t_f32 >= (current_time - 2.5) as f32 && t_f32 <= (current_time + 2.5) as f32
    
            })
        })
        .collect();

    let relevant_data = data_frame_resource.0.filter(&mask).unwrap();

    let width = 1920.0;
    let height = 1080.0;

    // Define padding as a percentage of the height
    let padding_percent = 0.0; // 15% padding at the bottom
    let padding_bottom = height * padding_percent;

    let max_frequency = audio_analysis_data.max_frequency;
    let min_frequency = audio_analysis_data.min_frequency;
    let min_loudness = audio_analysis_data.min_loudness;
    let max_loudness = audio_analysis_data.max_loudness;
    // Adjust scale_y to fit within the screen, considering padding
    let scale_y = (height - padding_bottom) / (max_frequency - min_frequency);
    let scale_x = width / 5.0;

    // Process `relevant_data` as needed
    for i in 0..relevant_data.height() {
        let time = relevant_data
            .column("time")
            .unwrap()
            .f64()
            .unwrap()
            .get(i)
            .unwrap() as f32;
        let frequency = relevant_data
            .column("frequency")
            .unwrap()
            .f64()
            .unwrap()
            .get(i)
            .unwrap() as f32;
        let loudness = relevant_data
            .column("loudness")
            .unwrap()
            .f64()
            .unwrap()
            .get(i)
            .unwrap() as f32;

        let mut x = (time - current_time + 2.5) * scale_x;
        let mut y = (height - padding_bottom) - (frequency - min_frequency) * scale_y;
        y = y - 800.0;
        x = x - 1500.0;
        // pprint y
        println!("y is coming......");
        print!("{} ", y);
        let circle_size = loudness_to_size(loudness, min_loudness, max_loudness);

        let shape = shapes::Circle {
            radius: circle_size,     // Use the calculated circle size
            center: Vec2::new(x, y), // Use the calculated x, y position
        };

        commands.spawn((
            ShapeBundle {
                path: GeometryBuilder::build_as(&shape),
                ..default()
            },
            Fill::color(Color::CYAN),
            Stroke::new(
                Color::Rgba {
                    red: (1.0),
                    green: (0.6),
                    blue: (0.2),
                    alpha: (0.8),
                },
                1.0,
            ),
        ));
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("Usage: program <features.csv> <audio.wav>");
        return;
    }
    let features_path = &args[1];
    let audio_path = args[2].clone();

    let duration = match get_wav_duration(format!("assets/{}", audio_path)) {
        Ok(d) => d,
        Err(e) => {
            eprintln!("Error reading WAV file: {}", e);
            return;
        }
    };
    println!("Duration: {}", duration);

    // Read CSV file using Polars
    let df = CsvReader::from_path(features_path)
        .expect("Failed to read CSV file")
        .finish()
        .expect("Failed to load CSV data");

    let min_frequency = df
        .column("frequency")
        .unwrap()
        .f64()
        .unwrap()
        .min()
        .unwrap() as f32;
    let max_frequency = df
        .column("frequency")
        .unwrap()
        .f64()
        .unwrap()
        .max()
        .unwrap() as f32;
    let min_loudness = df.column("loudness").unwrap().f64().unwrap().min().unwrap() as f32;
    let max_loudness = df.column("loudness").unwrap().f64().unwrap().max().unwrap() as f32;

    App::new()
        .insert_resource(ClearColor(Color::rgb(0.4, 0.6, 0.6)))
        .insert_resource(AudioAnalysisData {
            min_frequency,
            max_frequency,
            min_loudness,
            max_loudness,
        })
        .insert_resource(DataFrameResource(df))
        .insert_resource(AudioFile {
            path: audio_path.to_string(),
            duration: duration,
        })
        .add_systems(Startup, add_camera)
        .add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                title: "I am a window!".into(),
                resolution: (1920., 1080.).into(),
                present_mode: PresentMode::AutoVsync,
                // Tells wasm to resize the window according to the available canvas
                fit_canvas_to_parent: true,
                // Tells wasm not to override default event handling, like F5, Ctrl+R etc.
                prevent_default_event_handling: false,
                window_theme: Some(WindowTheme::Dark),
                enabled_buttons: bevy::window::EnabledButtons {
                    maximize: false,
                    ..Default::default()
                },
                // This will spawn an invisible window
                // The window will be made visible in the make_visible() system after 3 frames.
                // This is useful when you want to avoid the white window that shows up before the GPU is ready to render the app.
                visible: true,
                ..default()
            }),
            ..default()
        }))
        .add_plugins((FPSPlugin, AudioPlayerPlugin))
        .add_plugins(ShapePlugin)
        .add_systems(Startup, add_line)
        .add_systems(Update, filter_data_system)
        .run();
}
