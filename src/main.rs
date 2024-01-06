mod fps;
use bevy::prelude::*;
use bevy_prototype_lyon::prelude::*;
use fps::FPSPlugin;


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
        Stroke::new(Color::Rgba { red: (1.0), green: (0.6), blue: (0.2), alpha: (0.8) }, 1.0),
    ));
}

fn main() {
    App::new()
        .insert_resource(ClearColor(Color::rgb(0.4, 0.6, 0.6)))
        .add_systems(Startup, add_camera)
        .add_plugins((DefaultPlugins, FPSPlugin))
        .add_plugins(ShapePlugin)
        .add_systems(Startup, add_line)
        .run();
}
