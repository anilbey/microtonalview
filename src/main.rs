mod fps;
use std::path::Path;
use std::{env, time::Duration};

use bevy::app::AppExit;
use bevy_kira_audio::{Audio, AudioControl, AudioPlugin};

use bevy::prelude::*;
use bevy_prototype_lyon::prelude::*;
use fps::FPSPlugin;
use polars::{
    chunked_array::ops::ChunkAgg,
    io::{csv::CsvReader, SerReader},
};

fn get_wav_duration<P: AsRef<Path>>(file_path: P) -> Result<f32, hound::Error> {
    let reader = hound::WavReader::open(file_path)?;
    let spec = reader.spec();
    let duration = reader.duration() as f32 / spec.sample_rate as f32;
    Ok(duration)
}

#[derive(Resource)]
struct AudioAnalysisData {
    min_frequency: f64,
    max_frequency: f64,
    min_loudness: f64,
    max_loudness: f64,
}

#[derive(Resource)]
struct AudioFile {
    path: String,
    duration: f32,
}

#[derive(Resource)]
struct AudioTimer(Timer);

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

fn play_audio(
    audio: Res<Audio>,
    asset_server: Res<AssetServer>,
    audio_file: Res<AudioFile>,
    mut timer: ResMut<AudioTimer>,
) {
    let audio_handle = asset_server.load(&audio_file.path);
    audio.play(audio_handle);
    timer
        .0
        .set_duration(Duration::from_secs_f32(audio_file.duration));
    timer.0.reset();
}

// check the timer to exit the app
fn check_audio_timer(
    time: Res<Time>,
    mut timer: ResMut<AudioTimer>,
    mut app_exit_events: EventWriter<AppExit>,
) {
    if timer.0.tick(time.delta()).just_finished() {
        app_exit_events.send(AppExit);
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
        .unwrap();
    let max_frequency = df
        .column("frequency")
        .unwrap()
        .f64()
        .unwrap()
        .max()
        .unwrap();
    let min_loudness = df.column("loudness").unwrap().f64().unwrap().min().unwrap();
    let max_loudness = df.column("loudness").unwrap().f64().unwrap().max().unwrap();

    App::new()
        .insert_resource(ClearColor(Color::rgb(0.4, 0.6, 0.6)))
        .insert_resource(AudioAnalysisData {
            min_frequency,
            max_frequency,
            min_loudness,
            max_loudness,
        })
        .insert_resource(AudioFile {
            path: audio_path.to_string(),
            duration: duration,
        })
        .insert_resource(AudioTimer(Timer::from_seconds(0.0, TimerMode::Once)))
        .add_systems(Startup, add_camera)
        .add_plugins((DefaultPlugins, FPSPlugin))
        .add_plugins(AudioPlugin)
        .add_plugins(ShapePlugin)
        .add_systems(Startup, add_line)
        .add_systems(Startup, play_audio)
        .add_systems(Update, check_audio_timer)
        .run();
}
