## START import and setup
import pygame
import pygame_gui
import sys

pygame.init()

# Set up the display
window_size = (1000, 700)
window_surface = pygame.display.set_mode(window_size)
pygame.display.set_caption('Pygame GUI Builder')

background = pygame.Surface(window_size)
background.fill(pygame.Color('#222222'))

# UI Manager
try:
    manager = pygame_gui.UIManager(window_size, 'theme.json')
except FileNotFoundError:
    print("Warning: theme.json not found. Using default theme.")
    manager = pygame_gui.UIManager(window_size)
## END import and setup

## START panels and element definitions
# Panels
menu_panel = pygame_gui.elements.UIPanel(
    relative_rect=pygame.Rect(0, 0, 200, 700),
    manager=manager,
    starting_height=1,
    anchors={'left': 'left', 'right': 'left', 'top': 'top', 'bottom': 'bottom'}
)

canvas_panel_rect = pygame.Rect(200, 0, 800, 700)
canvas_panel = pygame_gui.elements.UIPanel(
    relative_rect=canvas_panel_rect,
    manager=manager,
    starting_height=1,
    anchors={'left': 'left', 'right': 'right', 'top': 'top', 'bottom': 'bottom'}
)

# Element definitions
element_types = [
    {'name': 'Button', 'class': pygame_gui.elements.UIButton, 'text': 'Button'},
    {'name': 'Label', 'class': pygame_gui.elements.UILabel, 'text': 'Label'},
    {'name': 'Text Box', 'class': pygame_gui.elements.UITextBox, 'text': '<b>Text Box</b>'},
    {'name': 'Text Entry', 'class': pygame_gui.elements.UITextEntryLine},
    {'name': 'Slider', 'class': pygame_gui.elements.UIHorizontalSlider, 'value_range': [0, 100], 'start_value': 50},
    {'name': 'Progress Bar', 'class': pygame_gui.elements.UIProgressBar},
    {'name': 'Drop Down', 'class': pygame_gui.elements.UIDropDownMenu,
     'options_list': ['Option 1', 'Option 2'], 'starting_option': 'Option 1'}
]

# Menu buttons
y_pos = 10
for element_type in element_types:
    pygame_gui.elements.UIButton(
        relative_rect=pygame.Rect(10, y_pos, 180, 30),
        text=element_type['name'],
        manager=manager,
        container=menu_panel,
        object_id=pygame_gui.core.ObjectID(class_id=element_type['name'].replace(' ', '_').lower())
    )
    y_pos += 40
## END panels and element definitions

## START state and clock
# State
canvas_elements = []
selected_element = None
drag_offset = (0, 0)

clock = pygame.time.Clock()
is_running = True
## END state and clock

## START popup menu state
popup_menu = None
popup_menu_target = None  # The element selected for deletion via popup
## END popup menu state

## START main loop
just_added_element = False  # Cooldown flag

while is_running:
    time_delta = clock.tick(60) / 1000.0

    mouse_pos = pygame.mouse.get_pos()
    local_mouse = (mouse_pos[0] - canvas_panel_rect.x, mouse_pos[1])

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            is_running = False

        if event.type == pygame_gui.UI_BUTTON_PRESSED and not just_added_element:
            button_id = event.ui_object_id

            for element_type in element_types:
                expected_id = f'panel.{element_type["name"].replace(" ", "_").lower()}'
                if button_id == expected_id:
                    element_offset = len(canvas_elements) * 10
                    default_rect = pygame.Rect(50 + element_offset, 50 + element_offset, 150, 40)

                    args = {
                        'relative_rect': default_rect,
                        'manager': manager,
                        'container': canvas_panel,
                        'object_id': pygame_gui.core.ObjectID()
                    }

                    if 'text' in element_type:
                        if element_type['class'] == pygame_gui.elements.UITextBox:
                            args['html_text'] = element_type['text']
                        else:
                            args['text'] = element_type['text']

                    if 'value_range' in element_type:
                        args['value_range'] = element_type['value_range']
                        args['start_value'] = element_type['start_value']
                    if 'options_list' in element_type:
                        args['options_list'] = element_type['options_list']
                        args['starting_option'] = element_type['starting_option']

                    new_elem = element_type['class'](**args)
                    canvas_elements.append(new_elem)

                    just_added_element = True  # Set cooldown flag
                    break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if canvas_panel_rect.collidepoint(mouse_pos):
                for element in reversed(canvas_elements):
                    if element.relative_rect.collidepoint(local_mouse):
                        selected_element = element
                        drag_offset = (
                            local_mouse[0] - element.relative_rect.x,
                            local_mouse[1] - element.relative_rect.y
                        )
                        break

        elif event.type == pygame.MOUSEMOTION:
            if selected_element:
                new_x = local_mouse[0] - drag_offset[0]
                new_y = local_mouse[1] - drag_offset[1]

                new_x = max(0, min(new_x, canvas_panel_rect.width - selected_element.relative_rect.width))
                new_y = max(0, min(new_y, canvas_panel_rect.height - selected_element.relative_rect.height))

                selected_element.set_relative_position((new_x, new_y))

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            selected_element = None
            just_added_element = False  # Reset cooldown on mouse release

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if canvas_panel_rect.collidepoint(mouse_pos):
                for element in reversed(canvas_elements):
                    if element.relative_rect.collidepoint(local_mouse):
                        # If popup menu exists, remove it first
                        if popup_menu is not None:
                            popup_menu.kill()
                            popup_menu = None
                            popup_menu_target = None

                        # Create popup menu with "Delete"
                        popup_menu = pygame_gui.elements.UISelectionList(
                            relative_rect=pygame.Rect(mouse_pos[0], mouse_pos[1], 120, 50),
                            item_list=["Delete"],
                            manager=manager,
                            container=None,
                            object_id=pygame_gui.core.ObjectID(class_id='popup_menu')
                        )
                        popup_menu_target = element
                        break


        elif event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            if popup_menu is not None and event.ui_element == popup_menu:
                selected_text = event.text
                if selected_text == "Delete" and popup_menu_target in canvas_elements:
                    popup_menu_target.kill()
                    canvas_elements.remove(popup_menu_target)

                popup_menu.kill()
                popup_menu = None
                popup_menu_target = None

        manager.process_events(event)

    manager.update(time_delta)

    window_surface.blit(background, (0, 0))
    manager.draw_ui(window_surface)

    pygame.display.update()
## END main loop

## START cleanup
pygame.quit()
sys.exit()
## END cleanup