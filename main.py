import flet as ft
import sqlite3
import base64
import os
import shutil
from PIL import Image
import io

# ================= CONFIGURATION =================
DB_FILENAME = "Ward11_Only.db"

def get_db_path():
    try:
        return os.path.join(os.getcwd(), DB_FILENAME)
    except:
        return DB_FILENAME

DB_PATH = get_db_path()

def configure_mobile_db():
    if not os.path.exists(DB_PATH):
        asset_db_path = os.path.join("assets", DB_FILENAME)
        if os.path.exists(asset_db_path):
            try:
                shutil.copy(asset_db_path, DB_PATH)
            except Exception as e:
                print(f"Error copying DB: {e}")

configure_mobile_db()

# ================= DATABASE HELPERS =================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            id INTEGER PRIMARY KEY,
            header_path TEXT,
            cand_name TEXT,
            cand_party TEXT,
            cand_symbol TEXT
        )
    """)
    cursor.execute("SELECT count(*) FROM app_settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO app_settings (id, header_path, cand_name, cand_party, cand_symbol) VALUES (1, '', '', '', '')")
    conn.commit()
    conn.close()

def save_settings_to_db(header, name, party, symbol):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE app_settings 
        SET header_path=?, cand_name=?, cand_party=?, cand_symbol=? 
        WHERE id=1
    """, (header, name, party, symbol))
    conn.commit()
    conn.close()

def load_settings_from_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT header_path, cand_name, cand_party, cand_symbol FROM app_settings WHERE id=1")
    row = cursor.fetchone()
    conn.close()
    return row if row else ("", "", "", "")

def get_voter_data(query):
    if not os.path.exists(DB_PATH): return []
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        sql = f"""
        SELECT srno, vcardid, l_voter_name, age, sex, l_boothaddress, 
               part_no, assembly_mapping, l_address
        FROM voters 
        WHERE vcardid = '{query}' 
           OR l_voter_name LIKE '%{query}%' 
           OR e_voter_name LIKE '%{query}%'
        LIMIT 10
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"DB Error: {e}")
        return []

# --- SUPER AGGRESSIVE IMAGE COMPRESSION ---
def get_image_base64(path):
    if not path or path.strip() == "":
        return ""
    if not os.path.exists(path):
        asset_path = os.path.join("assets", os.path.basename(path))
        if os.path.exists(asset_path):
            path = asset_path
            
    if path and os.path.exists(path) and os.path.isfile(path):
        try:
            img = Image.open(path)
            
            # 1. Convert to Black & White (Grayscale) - Saves huge space
            img = img.convert("L") 
            
            # 2. Resize very small (Thumbnail size is enough for thermal)
            base_width = 200 
            w_percent = (base_width / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((base_width, h_size), Image.Resampling.NEAREST)
            
            # 3. Save as JPEG with Low Quality
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=30) 
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Image Error: {e}")
            return ""
    return ""

# ================= MAIN APP UI =================
def main(page: ft.Page):
    page.title = "Giriraj Voter App"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.ADAPTIVE
    page.padding = 10
    page.bgcolor = ft.Colors.GREY_100
    
    init_db()
    saved_header_path, saved_cand, saved_party, saved_symbol = load_settings_from_db()
    header_img_path = ft.Ref[str]()
    header_img_path.current = saved_header_path

    # --- UI Controls ---
    txt_cand_name = ft.TextField(label="उमेदवार (Name)", value=saved_cand)
    txt_party = ft.TextField(label="पार्टी (Party)", value=saved_party)
    txt_symbol = ft.TextField(label="निशाणी (Symbol)", value=saved_symbol)
    txt_header_status = ft.Text(value="Image Selected" if saved_header_path else "No Image", color=ft.Colors.GREEN if saved_header_path else ft.Colors.RED)
    search_box = ft.TextField(label="नाव किंवा EPIC नंबर टाका...", expand=True)

    # --- UNIVERSAL HTML PRINTER (NO RAWBT, NO BOXES) ---
    def print_slip_html(voter, with_photo=True):
        try:
            # Data Setup
            c_name = txt_cand_name.value if txt_cand_name.value else ""
            c_party = txt_party.value if txt_party.value else ""
            c_sym = txt_symbol.value if txt_symbol.value else ""
            
            img_html = ""
            if with_photo:
                h_path = header_img_path.current
                img_b64 = get_image_base64(h_path)
                if img_b64:
                    img_html = f'<img src="data:image/jpeg;base64,{img_b64}" class="header-img">'
            
            gender = "M" if voter[4] == "M" else "F" if voter[4] == "F" else str(voter[4])
            v_vals = [str(x) if x else "" for x in voter]

            # CSS: Force Black & White, High Contrast
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Voter Slip</title>
                <style>
                    @page {{ size: auto; margin: 0mm; }}
                    body {{ 
                        font-family: 'Noto Sans', sans-serif; 
                        margin: 0; padding: 5px; 
                        width: 100%; background: #fff; color: #000;
                    }}
                    .container {{ 
                        width: 100%; max-width: 350px; margin: 0 auto; 
                        text-align: center; border: 2px dashed #000; padding: 5px;
                    }}
                    .header-img {{ width: 80%; max-height: 100px; object-fit: contain; display: block; margin: 0 auto; filter: grayscale(100%); }}
                    .cand-box {{ 
                        border: 2px solid #000; border-radius: 5px; 
                        padding: 5px; margin: 5px 0; 
                        font-weight: bold; font-size: 16px; line-height: 1.4;
                    }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 5px; text-align: left; }}
                    td {{ padding: 2px; vertical-align: top; font-size: 15px; color: #000; font-weight: 600; }}
                    .big {{ font-size: 18px; font-weight: bold; }}
                    .print-btn {{
                        display: block; width: 100%; padding: 15px; 
                        background: #000; color: white; text-align: center; 
                        font-size: 20px; margin-top: 10px; text-decoration: none;
                    }}
                    @media print {{ .print-btn {{ display: none; }} }}
                </style>
            </head>
            <body>
                <div class="container">
                    {img_html}
                    <div class="cand-box">
                        {c_name}<br>{c_party}<br>{c_sym}
                    </div>
                    <div style="font-size: 12px;">✂ ------------------------- ✂</div>
                    <table>
                        <tr><td colspan="2" class="big">Name: {v_vals[2]}</td></tr>
                        <tr><td colspan="2"><hr style="border-top: 1px solid #000;"></td></tr>
                        <tr><td>Ward: <b style="font-size:18px;">{v_vals[6]}</b></td><td>Sr.No: <b style="font-size:18px;">{v_vals[0]}</b></td></tr>
                        <tr><td>Age: {v_vals[3]}</td><td>Sex: {gender}</td></tr>
                        <tr><td colspan="2" class="big" style="border:2px solid #000; padding:5px; text-align:center; margin:5px 0;">EPIC: {v_vals[1]}</td></tr>
                        <tr><td colspan="2" style="font-size:12px;">Addr: {v_vals[8]}</td></tr>
                        <tr><td colspan="2" class="big" style="padding-top:5px;">Booth: {v_vals[5]}</td></tr>
                    </table>
                    <br>
                    <div style="font-size: 10px;">Powered by Giriraj App</div>
                    <br>
                    <a href="javascript:window.print()" class="print-btn">🖨️ CLICK TO PRINT</a>
                </div>
            </body>
            </html>
            """
            html_b64 = base64.b64encode(html.encode('utf-8')).decode('utf-8')
            page.launch_url(f"data:text/html;base64,{html_b64}")
            
            page.snack_bar = ft.SnackBar(ft.Text("Opening... Click 'Print' in Browser!"))
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {e}"))
            page.snack_bar.open = True
            page.update()

    # --- PREVIEW UI ---
    def show_preview(e, voter):
        # Dialog to choose mode
        dlg = ft.AlertDialog(
            title=ft.Text("Print Selection"),
            content=ft.Column([
                ft.Text(f"Voter: {voter[2]}", weight="bold"),
                ft.Divider(),
                ft.ElevatedButton("1. Print With Photo 📸", 
                                  on_click=lambda _: print_slip_html(voter, with_photo=True), 
                                  bgcolor=ft.Colors.BLUE, color="white", width=250),
                ft.Text("Agar ye open na ho, to niche wala dabayein 👇", size=10, color="red"),
                ft.ElevatedButton("2. Print SAFE MODE (No Photo) 📄", 
                                  on_click=lambda _: print_slip_html(voter, with_photo=False), 
                                  bgcolor=ft.Colors.GREEN, color="white", width=250),
                ft.Text("Ye 100% open hoga aur Marathi sahi aayegi.", size=10, color="grey"),
            ], height=220, alignment=ft.MainAxisAlignment.CENTER, spacing=10),
        )
        page.open(dlg)

    # --- SEARCH ---
    results_col = ft.Column(scroll=ft.ScrollMode.AUTO)
    def do_search(query):
        results_col.controls.clear()
        if not query: return
        data = get_voter_data(query)
        if not data:
            results_col.controls.append(ft.Text("डेटा सापडला नाही!", color=ft.Colors.RED))
        else:
            for row in data:
                card = ft.Card(content=ft.Container(padding=10, bgcolor=ft.Colors.WHITE, border_radius=10, content=ft.Column([
                            ft.Text(f"{row[2]}", size=16, weight="bold", color="black"),
                            ft.Text(f"EPIC: {row[1]} | Sr: {row[0]}", color="black"),
                            ft.Divider(),
                            ft.ElevatedButton("PRINT MENU 🖨️", on_click=lambda e, r=row: show_preview(e, r), bgcolor=ft.Colors.ORANGE, color="white")
                        ])))
                results_col.controls.append(card)
        page.update()

    def on_search_click(e): do_search(search_box.value)

    # --- SETTINGS ---
    def pick_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            header_img_path.current = e.files[0].path
            txt_header_status.value = "Image Selected"
            page.update()

    file_picker = ft.FilePicker(on_result=pick_file_result)
    page.overlay.append(file_picker)

    def save_settings(e):
        save_settings_to_db(header_img_path.current, txt_cand_name.value, txt_party.value, txt_symbol.value)
        page.snack_bar = ft.SnackBar(ft.Text("Settings Saved!"))
        page.snack_bar.open = True
        page.update()

    settings_col = ft.Column([
        ft.ElevatedButton("Select Header Image", icon=ft.Icons.IMAGE, on_click=lambda _: file_picker.pick_files()),
        txt_header_status, txt_cand_name, txt_party, txt_symbol,
        ft.ElevatedButton("Save Settings", on_click=save_settings, bgcolor="blue", color="white")
    ], visible=False)

    page.add(
        ft.Row([ft.Text("Voter App", size=20, weight="bold"), ft.IconButton(ft.Icons.SETTINGS, on_click=lambda _: setattr(settings_col, 'visible', not settings_col.visible) or page.update())], alignment="spaceBetween"),
        settings_col, ft.Divider(),
        ft.Row([search_box, ft.IconButton(ft.Icons.SEARCH, on_click=on_search_click)]),
        results_col
    )

if __name__ == "__main__":
    ft.app(target=main)
