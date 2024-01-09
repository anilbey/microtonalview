use std::time::Duration;

use bevy::{app::AppExit, prelude::*};
use bevy_kira_audio::{Audio, AudioControl, AudioPlugin};

pub struct AudioPlayerPlugin;

#[derive(Resource)]
struct AudioTimer(Timer);

#[derive(Resource)]
pub struct AudioFile {
    pub(crate) path: String,
    pub(crate) duration: f32,
}

impl Plugin for AudioPlayerPlugin {
    fn build(&self, app: &mut App) {
        app.add_plugins(AudioPlugin)
            .insert_resource(AudioTimer(Timer::from_seconds(0.0, TimerMode::Once)))
            .add_systems(Startup, play_audio)
            .add_systems(Update, check_audio_timer);
    }
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
