# Standard library imports
import colorsys
import random
import time
import sys

# Third-party imports with better error handling
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Error: Pygame is required to run this game.")
    print("Please install it with: pip install pygame")

def hsv_to_rgb_tuple(h, s, v):
    """Converts HSV to an RGB tuple (0-255)."""
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)

def generate_target_hue():
    """Generates a random target hue."""
    return random.random()  # Hue is a float from 0.0 to 1.0

def create_color_rect(rgb, size=(100, 100)):
    """Creates a Pygame Surface filled with an RGB tuple (0-255)."""
    if not PYGAME_AVAILABLE:
        sys.exit(1)
    w, h = int(size[0]), int(size[1])
    rect_surface = pygame.Surface((w, h))
    rect_surface.fill(rgb)
    if pygame.get_init() and pygame.display.get_surface() is not None:
        try:
            rect_surface = rect_surface.convert()
        except Exception:
            pass
    return rect_surface

def rgb_distance(c1, c2):
    """Return Euclidean distance between two RGB tuples (0-255)."""
    dr = c1[0] - c2[0]
    dg = c1[1] - c2[1]
    db = c1[2] - c2[2]
    return (dr * dr + dg * dg + db * db) ** 0.5

def draw_sunrise_background(surface):
    """Draw a sunrise gradient background from dark blue/purple at top to orange/yellow at bottom."""
    width, height = surface.get_size()
    for y in range(height):
        progress = y / height
        # Transition from dark blue/purple -> pink -> orange -> yellow
        if progress < 0.3:
            # Dark blue to purple
            t = progress / 0.3
            r = int(20 + (60 - 20) * t)
            g = int(10 + (20 - 10) * t)
            b = int(50 + (80 - 50) * t)
        elif progress < 0.6:
            # Purple to pink/orange
            t = (progress - 0.3) / 0.3
            r = int(60 + (255 - 60) * t)
            g = int(20 + (120 - 20) * t)
            b = int(80 + (60 - 80) * t)
        else:
            # Pink/orange to yellow
            t = (progress - 0.6) / 0.4
            r = int(255)
            g = int(120 + (200 - 120) * t)
            b = int(60 + (100 - 60) * t)
        
        pygame.draw.line(surface, (r, g, b), (0, y), (width, y))

class GameState:
    """Track game state and score."""
    def __init__(self):
        self.running = True
        self.value = 0  # score/points
        self.state = 'playing'  # playing, win_display, win_dissolve
        self.grid_locked = False
        self.steps_taken = 0  # track number of block changes
        self.auto_mode = False  # auto cycling mode
        self.auto_timer = 0  # timer for auto cycling

def main():
    """Main game loop and initialization."""
    if not PYGAME_AVAILABLE:
        sys.exit(1)

    import pygame  # Ensure pygame is in local scope for all functions

    pygame.init()
    clock = pygame.time.Clock()
    WIDTH, HEIGHT = 800, 600
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("RSB Hue Match")

    # Create rainbow icon
    icon_size = 32
    icon = pygame.Surface((icon_size, icon_size))
    for x in range(icon_size):
        hue = x / icon_size
        color = hsv_to_rgb_tuple(hue, 1.0, 1.0)
        pygame.draw.line(icon, color, (x, 0), (x, icon_size))
    pygame.display.set_icon(icon)

    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    DARK_TEXT = (30, 30, 50)  # Dark blue-gray for text contrast
    GREEN = (0, 200, 0)

    pygame.font.init()
    try:
        font = pygame.font.SysFont("Yusbeau", 20)
    except Exception:
        try:
            font = pygame.font.SysFont("Century Gothic", 20)
        except Exception:
            try:
                font = pygame.font.Font(None, 20)
            except Exception:
                font = pygame.font.SysFont(None, 20)

    # GRID configuration
    GRID_COLS = 8
    GRID_ROWS = 6
    PADDING = 6
    SIDE_MARGIN = 20
    TOP_AREA = 140
    BOTTOM_MARGIN = 20

    # compute static layout values
    avail_w = WIDTH - 2 * SIDE_MARGIN - (GRID_COLS - 1) * PADDING
    avail_h = HEIGHT - TOP_AREA - BOTTOM_MARGIN - (GRID_ROWS - 1) * PADDING
    block_size = max(8, int(min(avail_w / GRID_COLS, avail_h / GRID_ROWS)))
    start_x = (WIDTH - (block_size * GRID_COLS + PADDING * (GRID_COLS - 1))) // 2
    start_y = TOP_AREA
    total = GRID_COLS * GRID_ROWS

    def reset_game():
        """Initialize or reset the game state."""
        # create target gradient
        offset = random.random()
        target_hues = [(offset + i / total) % 1.0 for i in range(total)]
        target_rgbs = [hsv_to_rgb_tuple(h, 1.0, 1.0) for h in target_hues]
        
        # shuffle starting hues
        current_hues = target_hues.copy()
        random.shuffle(current_hues)
        
        # create blocks
        blocks = []
        positions = []
        for idx in range(total):
            r = idx // GRID_COLS
            c = idx % GRID_COLS
            x = start_x + c * (block_size + PADDING)
            y = start_y + r * (block_size + PADDING)
            positions.append((x, y))

        for i, hue in enumerate(current_hues):
            rgb = hsv_to_rgb_tuple(hue, 1.0, 1.0)
            x, y = positions[i]
            blocks.append({
                "hue": hue, 
                "rgb": rgb, 
                "x": x, 
                "y": y, 
                "matched": False, 
                "locked": False,
                "clicked": False  # Add clicked state
            })

        # Check initial matches and lock if needed
        grid_locked = False
        for i, b in enumerate(blocks):
            if rgb_distance(b["rgb"], target_rgbs[i]) < 30.0:
                b["matched"] = True
                b["hue"] = target_hues[i]
                b["rgb"] = hsv_to_rgb_tuple(b["hue"], 1.0, 1.0)
                b["locked"] = True
                grid_locked = True

        # find first unlocked block for selection
        selected = 0
        for i, b in enumerate(blocks):
            if not b["locked"]:
                selected = i
                blocks[i]["clicked"] = True  # Mark initial selection as clicked
                break
        
        return blocks, target_hues, target_rgbs, selected, grid_locked

    # Initial game state
    blocks, target_hues, target_rgbs, selected, grid_locked = reset_game()
    cell_target_rgb = target_rgbs

    # Game states and timing
    PLAYING = 'playing'
    WIN_DISPLAY = 'win_display'
    WIN_DISSOLVE = 'win_dissolve'
    
    # Replace timing constants with block counts and add notice duration
    HUE_STEP = 1/36.0
    MOVES_PER_DISSOLVE = 60  # number of blocks to wait before dissolve
    NOTICE_DURATION = 1.5  # seconds to show notices
    AUTO_CYCLE_SPEED = 0.05  # seconds between auto hue changes

    # Remove timing variables, add block counters
    game = GameState()
    dissolve_blocks = 0
    now = time.time()  # Initialize current time
    locked_notice_until = 0  # Initialize notice timer

    def update_block_rgb(b):
        b["rgb"] = hsv_to_rgb_tuple(b["hue"] % 1.0, 1.0, 1.0)

    def move_selection(start, delta):
        """Move selection by delta, skipping locked blocks. Returns new selected index."""
        if all(b["locked"] for b in blocks):
            return start  # all blocks locked, can't move
        
        next_idx = start
        for _ in range(total):  # prevent infinite loop
            next_idx = (next_idx + delta) % total
            if not blocks[next_idx]["locked"]:
                return next_idx
        return start  # fallback if no unlocked found

    def handle_block_click(pos):
        """Handle mouse click on blocks, return True if block was selected."""
        for idx, b in enumerate(blocks):
            if not b["locked"]:
                rect = pygame.Rect(b["x"], b["y"], block_size, block_size)
                if rect.collidepoint(pos):
                    # Reset clicked state for all blocks
                    for block in blocks:
                        block["clicked"] = False
                    # Set new selection
                    blocks[idx]["clicked"] = True
                    return idx
        return None

    def check_and_lock_block(block_idx):
        """Check if block matches target and lock if matched."""
        if rgb_distance(blocks[block_idx]["rgb"], cell_target_rgb[block_idx]) < 30.0:
            blocks[block_idx]["matched"] = True
            blocks[block_idx]["hue"] = target_hues[block_idx]
            update_block_rgb(blocks[block_idx])
            blocks[block_idx]["locked"] = True
            return True
        return False

    def draw_block_with_opacity(surface, block, opacity):
        """Draw a block with given opacity (0-255)."""
        x, y = block["x"], block["y"]
        surf = create_color_rect(block["rgb"], size=(block_size, block_size))
        if opacity < 255:
            surf.set_alpha(opacity)
        surface.blit(surf, (x, y))

    while game.running:
        dt = clock.tick(60) / 1000.0
        now = time.time()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game.running = False
            
            if game.state == PLAYING:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    new_selected = handle_block_click(pygame.mouse.get_pos())
                    if new_selected is not None:
                        selected = new_selected

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        if not game.grid_locked:
                            blocks, target_hues, target_rgbs, selected, grid_locked = reset_game()
                            cell_target_rgb = target_rgbs
                            locked_notice_until = 0  # reset notice
                        else:
                            locked_notice_until = now + NOTICE_DURATION

                    elif event.key == pygame.K_TAB:
                        game.auto_mode = not game.auto_mode
                        game.auto_timer = now

                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        selected = move_selection(selected, 1)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        selected = move_selection(selected, -1)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        selected = move_selection(selected, GRID_COLS)
                    elif event.key == pygame.K_UP or event.key == pygame.K_w:
                        selected = move_selection(selected, -GRID_COLS)

                    elif event.key == pygame.K_SPACE:
                        if not blocks[selected]["locked"]:
                            blocks[selected]["hue"] = (blocks[selected]["hue"] + HUE_STEP) % 1.0
                            update_block_rgb(blocks[selected])
                            game.steps_taken += 1  # count block changes
                            
                            if check_and_lock_block(selected):
                                game.value += 10  # points for matching
                                if not game.grid_locked:
                                    game.grid_locked = True
                                if not all(b["locked"] for b in blocks):
                                    selected = move_selection(selected, 1)

        # Auto mode cycling
        if game.state == PLAYING and game.auto_mode:
            if now - game.auto_timer >= AUTO_CYCLE_SPEED:
                game.auto_timer = now
                if not blocks[selected]["locked"]:
                    blocks[selected]["hue"] = (blocks[selected]["hue"] + HUE_STEP) % 1.0
                    update_block_rgb(blocks[selected])
                    game.steps_taken += 1
                    
                    if check_and_lock_block(selected):
                        game.value += 10
                        if not game.grid_locked:
                            game.grid_locked = True
                        if not all(b["locked"] for b in blocks):
                            selected = move_selection(selected, 1)

        # Game state updates using block counts instead of time
        if game.state == PLAYING:
            if all(b["matched"] for b in blocks):
                game.state = WIN_DISPLAY
                game.value += 50  # bonus for completing grid
                dissolve_blocks = 0
        
        elif game.state == WIN_DISPLAY:
            game.state = WIN_DISSOLVE
        
        elif game.state == WIN_DISSOLVE:
            dissolve_blocks += 1
            progress = dissolve_blocks / MOVES_PER_DISSOLVE
            if progress >= 1.0:
                blocks, target_hues, target_rgbs, selected, grid_locked = reset_game()
                cell_target_rgb = target_rgbs
                game.state = PLAYING

        # draw
        draw_sunrise_background(screen)

        title = font.render("RSB Hue Match — align colors to the target gradient", True, WHITE)
        screen.blit(title, (SIDE_MARGIN, 10))
        instr = font.render("WASD/Arrows to navigate, SPACE to change hue. TAB: auto mode. R: reshuffle unlocked.", True, WHITE)
        screen.blit(instr, (SIDE_MARGIN, 36))
        
        # Show auto mode indicator
        if game.auto_mode:
            auto_indicator = font.render("AUTO MODE ON", True, (100, 255, 100))
            screen.blit(auto_indicator, (SIDE_MARGIN, 62))

        # draw small preview strip of first row targets
        preview_w = WIDTH - 2 * SIDE_MARGIN
        w = int(preview_w / GRID_COLS)
        for i in range(GRID_COLS):
            idx = i
            mini_rect = pygame.Rect(SIDE_MARGIN + i * w, TOP_AREA - 40, w, 24)
            pygame.draw.rect(screen, cell_target_rgb[idx], mini_rect)

        # show grid-lock notice if user tried to reshuffle after matching started
        if time.time() < locked_notice_until:
            notice = "Grid locked — reshuffle disabled after matching starts"
            notice_surf = font.render(notice, True, (255, 180, 0))
            screen.blit(notice_surf, (SIDE_MARGIN, TOP_AREA - 70))

        # Draw blocks with dissolve effect if in dissolve state
        if game.state == WIN_DISSOLVE:
            progress = dissolve_blocks / MOVES_PER_DISSOLVE
            opacity = int(255 * (1.0 - progress))
            for idx, b in enumerate(blocks):
                draw_block_with_opacity(screen, b, opacity)
                if b["matched"]:
                    pygame.draw.rect(screen, (*GREEN, opacity), 
                        pygame.Rect(b["x"] - 2, b["y"] - 2, block_size + 4, block_size + 4), 2)
        else:
            # Normal block drawing
            for idx, b in enumerate(blocks):
                x, y = b["x"], b["y"]
                surf = create_color_rect(b["rgb"], size=(block_size, block_size))
                screen.blit(surf, (x, y))
                # selection border only if selected and unlocked
                if idx == selected and not b["locked"]:
                    pygame.draw.rect(screen, WHITE, pygame.Rect(x - 3, y - 3, block_size + 6, block_size + 6), 3)
                # matched/locked border
                if b["matched"]:
                    pygame.draw.rect(screen, GREEN, pygame.Rect(x - 2, y - 2, block_size + 4, block_size + 4), 2)
                # subtle indicator for locked (dim inner border)
                if b["locked"]:
                    pygame.draw.rect(screen, (180, 180, 180), pygame.Rect(x + 3, y + 3, block_size - 6, block_size - 6), 1)

        # status
        matched_count = sum(1 for b in blocks if b["matched"])
        status = font.render(f"Matched: {matched_count}/{total}", True, DARK_TEXT)
        screen.blit(status, (SIDE_MARGIN, HEIGHT - 40))

        # score display
        value_text = font.render(f"Score: {game.value}", True, DARK_TEXT)
        screen.blit(value_text, (WIDTH - SIDE_MARGIN - value_text.get_width(), HEIGHT - 40))

        # win states display
        if game.state in (WIN_DISPLAY, WIN_DISSOLVE):
            victory = font.render("Gradient Complete! You win!", True, (255, 220, 0))
            rect = victory.get_rect(center=(WIDTH // 2, TOP_AREA // 2))
            screen.blit(victory, rect)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
