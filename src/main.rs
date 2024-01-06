use bevy::{
    diagnostic::{FrameTimeDiagnosticsPlugin, DiagnosticsStore},
    prelude::*, core_pipeline::clear_color::ClearColorConfig,
};

#[derive(Component)]
struct Person;

#[derive(Component)]
struct Name(String);

#[derive(Resource)]
struct GreetTimer(Timer);

#[derive(Component)]
struct FpsText;

pub struct HelloPlugin;

impl Plugin for HelloPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(GreetTimer(Timer::from_seconds(2.0, TimerMode::Repeating)))
            .add_systems(Startup, add_camera)
            .add_systems(Startup, add_people)
            .add_systems(Update, greet_people);
    }
}

fn add_camera(mut commands: Commands) {
    commands.spawn(Camera2dBundle::default());
}

fn add_people(mut commands: Commands, asset_server: Res<AssetServer>) {
    commands.spawn((Person, Name("Zayna Nieves".to_string())));

    // Create an entity for displaying FPS
    commands.spawn(TextBundle {
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

fn greet_people(
    time: Res<Time>, 
    mut timer: ResMut<GreetTimer>, 
    query: Query<&Name, With<Person>>) {
    if timer.0.tick(time.delta()).just_finished() {
        for name in query.iter() {
            println!("hello {}!", name.0);
        }
    }
}

fn update_fps(
    diagnostics: Res<DiagnosticsStore>,
    mut query: Query<&mut Text, With<FpsText>>,
) {
    for mut text in query.iter_mut() {
        if let Some(fps) = diagnostics.get(FrameTimeDiagnosticsPlugin::FPS) {
            if let Some(average) = fps.average() {
                text.sections[0].value = format!("FPS: {:.2}", average);
            }
        }
    }
}


fn main() {
    App::new()
        .insert_resource(ClearColor(Color::rgb(0.9, 0.3, 0.6)))
        .add_plugins((DefaultPlugins, HelloPlugin))
        .add_plugins(FrameTimeDiagnosticsPlugin::default())
        .add_systems(Update, update_fps)
        .run();
}
