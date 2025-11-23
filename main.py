import flet as ft
import sqlite3
import base64
import os
import shutil
from PIL import Image
import io
import urllib.parse # URL Encoding ke liye

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

# --- IMAGE COMPRESSION ---
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
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Resize for thermal print (Safe Width)
            base_width = 300
            w_percent = (base_width / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)
            
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=50) 
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Image Error: {e}")
            return ""
    return ""

# ================= MAIN APP UI =================
def main(page: ft.Page):
    page.title = "Voter Slip App"
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

    # --- METHOD 1: BROWSER PRINT (Thermal Safe) ---
    def print_via_browser(voter):
        try:
            c_name = txt_cand_name.value if txt_cand_name.value else ""
            c_party = txt_party.value if txt_party.value else ""
            c_sym = txt_symbol.value if txt_symbol.value else ""
            h_path = header_img_path.current
            img_b64 = get_image_base64(h_path)
            img_html = f'<img src="data:image/jpeg;base64,{img_b64}" class="header-img">' if img_b64 else ""
            
            gender = "M" if voter[4] == "M" else "F" if voter[4] == "F" else str(voter[4])
            v_vals = [str(x) if x else "" for x in voter]

            # --- CSS MAGIC FOR THERMAL PRINTER ---
            # @page { margin: 0 } -> Remove margins to prevent cutting
            # width: 100% -> Auto adapt to 58mm or 80mm
            html = f"""
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Voter Slip</title>
                <style>
                    @page {{ size: auto; margin: 0mm; }}
                    body {{ font-family: sans-serif; margin: 0; padding: 2px; width: 100%; background: #fff; }}
                    
                    .container {{ 
                        width: 100%; 
                        margin: 0 auto; 
                        text-align: center; 
                        padding: 0;
                    }}
                    
                    .header-img {{ width: 95%; max-height: 120px; object-fit: contain; display: block; margin: 0 auto; }}
                    
                    .cand-box {{ 
                        border: 2px solid #000; border-radius: 5px; 
                        padding: 5px; margin: 5px 2px; 
                        font-weight: bold; font-size: 14px; 
                    }}
                    
                    table {{ width: 100%; border-collapse: collapse; margin-top: 5px; text-align: left; }}
                    td {{ padding: 2px; vertical-align: top; font-size: 14px; color: #000; }}
                    
                    .bold {{ font-weight: bold; }}
                    .big {{ font-size: 16px; font-weight: bold; }}
                    
                    .btn-print {{ 
                        display: block; width: 90%; margin: 10px auto; padding: 12px; 
                        background: #000; color: white; text-align: center; 
                        text-decoration: none; font-size: 18px; border-radius: 5px; font-weight: bold;
                    }}
                    
                    /* Hide button when printing */
                    @media print {{ 
                        .btn-print {{ display: none; }} 
                        body {{ margin: 0; }}
                    }} 
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
                        <tr><td>Ward: <b>{v_vals[6]}</b></td><td>Sr.No: <b>{v_vals[0]}</b></td></tr>
                        <tr><td>Age: {v_vals[3]}</td><td>Sex: {gender}</td></tr>
                        <tr><td colspan="2" class="big" style="border:1px solid #000; padding:3px; display:inline-block; margin-top:3px;">EPIC: {v_vals[1]}</td></tr>
                        <tr><td colspan="2">AC: {v_vals[7]}</td></tr>
                        <tr><td colspan="2" style="font-size:12px;">Addr: {v_vals[8]}</td></tr>
                        <tr><td colspan="2" class="big" style="padding-top:5px;">Booth: {v_vals[5]}</td></tr>
                    </table>
                    <br>
                    <div style="font-size: 10px;">Powered by Giriraj Election App</div>
                    <br>
                    <!-- PRINT BUTTON -->
                    <a href="javascript:window.print()" class="btn-print">🖨️ PRINT NOW</a>
                </div>
            </body>
            </html>
            """
            html_b64 = base64.b64encode(html.encode('utf-8')).decode('utf-8')
            page.launch_url(f"data:text/html;base64,{html_b64}")
            
            page.snack_bar = ft.SnackBar(ft.Text("कृपया Paper Size (58mm/80mm) चेक करें!"))
            page.snack_bar.open = True
            page.update()
            
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"Browser Error: {e}"))
            page.snack_bar.open = True
            page.update()

    # --- METHOD 2: TEXT ONLY (Direct RawBT Backup) ---
    def print_text_only(voter):
        try:
            c_name = txt_cand_name.value
            gender = "M" if voter[4] == "M" else "F"
            # Adjusted for 58mm width
            text_data = (
                f"[C]<b>{c_name}</b>\n"
                f"[C]--------------------------------\n"
                f"[L]Name : <b>{voter[2]}</b>\n"
                f"[L]Ward: <b>{voter[6]}</b> [R]Sr.No: <b>{voter[0]}</b>\n"
                f"[L]EPIC : <b>{voter[1]}</b>\n"
                f"[L]Age  : {voter[3]}   Sex: {gender}\n"
                f"[L]Booth: {voter[5]}\n"
                f"[C]--------------------------------\n"
                f"[C]Powered by Giriraj App\n"
            )
            encoded_text = urllib.parse.quote(text_data)
            page.launch_url(f"rawbt:{encoded_text}")
        except Exception as e:
            print(f"Text Print Error: {e}")

    # --- PREVIEW ---
    def show_preview(e, voter):
        dlg = ft.AlertDialog(
            title=ft.Text("Select Print Mode"),
            content=ft.Column([
                ft.Text(f"Voter: {voter[2]}", weight="bold"),
                ft.Divider(),
                ft.ElevatedButton("Method 1: With Photo 📸", 
                                  on_click=lambda _: print_via_browser(voter), 
                                  bgcolor=ft.Colors.BLUE, color="white"),
                ft.Text("Best Quality (Use Chrome Print)", size=10, color="grey"),
                ft.Divider(),
                ft.ElevatedButton("Method 2: Fast / No Photo ⚡", 
                                  on_click=lambda _: print_text_only(voter), 
                                  bgcolor=ft.Colors.GREEN, color="white"),
                ft.Text("Works directly without browser", size=10, color="grey"),
            ], height=240, spacing=5),
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
                            ft.ElevatedButton("PRINT 🖨️", on_click=lambda e, r=row: show_preview(e, r), bgcolor=ft.Colors.ORANGE, color="white")
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
        page.snack_bar = ft.SnackBar(ft.Text("Saved!"))
        page.snack_bar.open = True
        page.update()

    settings_col = ft.Column([
        ft.ElevatedButton("Select Header Image", icon=ft.Icons.IMAGE, on_click=lambda _: file_picker.pick_files()),
        txt_header_status, txt_cand_name, txt_party, txt_symbol,
        ft.ElevatedButton("Save Settings", on_click=save_settings, bgcolor="blue", color="white")
    ], visible=False)

    page.add(
        ft.Row([ft.Text("Voter Print", size=20, weight="bold"), ft.IconButton(ft.Icons.SETTINGS, on_click=lambda _: setattr(settings_col, 'visible', not settings_col.visible) or page.update())], alignment="spaceBetween"),
        settings_col, ft.Divider(),
        ft.Row([search_box, ft.IconButton(ft.Icons.SEARCH, on_click=on_search_click)]),
        results_col
    )

if __name__ == "__main__":
    ft.app(target=main)
