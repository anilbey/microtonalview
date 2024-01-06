use bevy::{
    diagnostic::{DiagnosticsStore, FrameTimeDiagnosticsPlugin},
    prelude::*,
};

pub struct FPSPlugin;

#[derive(Component)]
struct FpsText;

impl Plugin for FPSPlugin {
    fn build(&self, app: &mut App) {
        app.add_plugins(FrameTimeDiagnosticsPlugin::default())
            .add_systems(Startup, add_fps_textbox)
            .add_systems(Update, update_fps);
    }
}

fn add_fps_textbox(mut commands: Commands, asset_server: Res<AssetServer>) {
    // Create an entity for displaying FPS
    commands
        .spawn(TextBundle {
            text: Text::from_section(
                "FPS: 0",
                TextStyle {
                    font: asset_server.load("fonts/FiraSans-Bold.ttf"), // Ensure this font is in your assets
                    font_size: 30.0,
                    color: Color::WHITE,
                },
            ),
            ..Default::default()
        })
        .insert(FpsText);
}

fn update_fps(diagnostics: Res<DiagnosticsStore>, mut query: Query<&mut Text, With<FpsText>>) {
    for mut text in query.iter_mut() {
        if let Some(fps) = diagnostics.get(FrameTimeDiagnosticsPlugin::FPS) {
            if let Some(average) = fps.average() {
                text.sections[0].value = format!("FPS: {:.2}", average);
            }
        }
    }
}
