import os, json, datetime, requests, urllib.parse, random, hashlib, threading, re
from flask import Flask, request, redirect, jsonify, make_response

app = Flask(__name__)

# ===================== DATABASE CONFIG =====================
DATABASE_URL = os.environ.get('DATABASE_URL', '')
USE_POSTGRES = DATABASE_URL.startswith('postgres')

if USE_POSTGRES:
    import psycopg2, psycopg2.extras
else:
    import sqlite3

DB_PATH = os.environ.get('DB_PATH', '/data/orders.db') if os.path.isdir('/data') else 'orders.db'
RESEND_KEY = os.environ.get('RESEND_API_KEY', '')
DASH_PASS = os.environ.get('DASHBOARD_PASS', 'vexora2024')
SITE_URL = os.environ.get('SITE_URL', 'https://vexoramaison.com')
RAILWAY_URL = os.environ.get('RAILWAY_URL', 'https://dropship-bot-production.up.railway.app')
FROM_EMAIL = 'Vexora Maison <orders@vexoramaison.com>'
REPLY_TO = 'support@vexoramaison.com'

# WooCommerce REST API config
WC_URL = os.environ.get('WC_URL', 'https://vexoramaison.com')
WC_KEY = os.environ.get('WC_KEY', '')
WC_SECRET = os.environ.get('WC_SECRET', '')
AUTO_NEWSLETTER_DAYS = 3

# ===================== NEWSLETTER TEMPLATES =====================
# Each template has RO and EN versions, subject + body HTML
NEWSLETTER_TEMPLATES = [
    {
        'id': 'pain_price',
        'subject': {'ro': 'Încă plătești 2000€ pe o pereche de adidași? 💸', 'en': 'Still paying 2000€ for a pair of sneakers? 💸'},
        'heading': {'ro': 'Serios Acum.', 'en': 'Let\'s Be Real.'},
        'body': {
            'ro': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Prietenii tăi plătesc <strong style="color:#fff">2000€</strong> pe o pereche de Nike Dunk.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Tu plătești <strong style="color:#c9a227">84.99€</strong> pentru <strong style="color:#fff">exact aceeași calitate</strong>. Materiale 1:1, cusături identice, box inclus.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Diferența? <strong style="color:#c9a227">1900€ rămân la tine.</strong></p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0 0 8px;color:#c9a227;font-size:22px;font-weight:800;letter-spacing:2px">CALITATE 1:1</p>
            <p style="margin:0;color:#999;font-size:13px">Aceleași materiale · Aceeași calitate · 1/10 din preț</p></div>''',
            'en': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Your friends pay <strong style="color:#fff">2000€</strong> for a pair of Nike Dunks.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">You pay <strong style="color:#c9a227">84.99€</strong> for <strong style="color:#fff">the exact same quality</strong>. 1:1 materials, identical stitching, box included.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">The difference? <strong style="color:#c9a227">1900€ stays in your pocket.</strong></p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0 0 8px;color:#c9a227;font-size:22px;font-weight:800;letter-spacing:2px">1:1 QUALITY</p>
            <p style="margin:0;color:#999;font-size:13px">Same materials · Same quality · 1/10 of the price</p></div>'''
        }
    },
    {
        'id': 'pain_wardrobe',
        'subject': {'ro': 'Garderoba ta de 500€ arată ca una de 5000€? 👀', 'en': 'Does your 500€ wardrobe look like a 5000€ one? 👀'},
        'heading': {'ro': 'Upgrade Masiv.', 'en': 'Massive Upgrade.'},
        'body': {
            'ro': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Imaginează-ți: <strong style="color:#fff">Dior, Louis Vuitton, Balenciaga</strong> în garderoba ta.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Nu la prețuri de retail. Nu la second hand uzat. Ci <strong style="color:#c9a227">brand new, calitate premium, 1:1</strong>.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Cu <strong style="color:#c9a227">74-89€</strong> ai un outfit complet care arată de 10x mai scump.</p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0 0 8px;color:#c9a227;font-size:22px;font-weight:800;letter-spacing:2px">LOOK PREMIUM</p>
            <p style="margin:0;color:#999;font-size:13px">Dior · LV · Balenciaga · Jordan · De la 74.99€</p></div>''',
            'en': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Imagine: <strong style="color:#fff">Dior, Louis Vuitton, Balenciaga</strong> in your wardrobe.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Not at retail prices. Not worn second hand. But <strong style="color:#c9a227">brand new, premium quality, 1:1</strong>.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">For <strong style="color:#c9a227">74-89€</strong> you get a full outfit that looks 10x more expensive.</p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0 0 8px;color:#c9a227;font-size:22px;font-weight:800;letter-spacing:2px">PREMIUM LOOK</p>
            <p style="margin:0;color:#999;font-size:13px">Dior · LV · Balenciaga · Jordan · From 74.99€</p></div>'''
        }
    },
    {
        'id': 'social_proof',
        'subject': {'ro': 'De ce 500+ clienți au ales Vexora Maison? 👑', 'en': 'Why 500+ customers chose Vexora Maison? 👑'},
        'heading': {'ro': 'Ei Deja Știu.', 'en': 'They Already Know.'},
        'body': {
            'ro': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Peste <strong style="color:#c9a227">500 de clienți</strong> din România și Europa au comandat deja.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Ce spun ei? Calitate ca originalul. Livrare rapidă. Prețuri care au sens. <strong style="color:#fff">Zero regrete.</strong></p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:20px;margin:20px 0">
            <p style="color:#ccc;font-size:14px;line-height:1.7;margin:0 0 12px;font-style:italic">"Am comandat Air Jordan 4 și nu pot să cred calitatea. Prietenii mei cred că sunt originale." — <strong style="color:#c9a227">Alex, București</strong></p>
            <p style="color:#ccc;font-size:14px;line-height:1.7;margin:0;font-style:italic">"Dior Tracksuit la 75€? Best purchase ever. Deja am comandat a doua oară." — <strong style="color:#c9a227">Maria, Cluj</strong></p></div>''',
            'en': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Over <strong style="color:#c9a227">500 customers</strong> from Romania and Europe have already ordered.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">What they say? Quality like the original. Fast delivery. Prices that make sense. <strong style="color:#fff">Zero regrets.</strong></p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:20px;margin:20px 0">
            <p style="color:#ccc;font-size:14px;line-height:1.7;margin:0 0 12px;font-style:italic">"I ordered Air Jordan 4 and can't believe the quality. My friends think they're real." — <strong style="color:#c9a227">Alex, Bucharest</strong></p>
            <p style="color:#ccc;font-size:14px;line-height:1.7;margin:0;font-style:italic">"Dior Tracksuit for 75€? Best purchase ever. Already ordered a second time." — <strong style="color:#c9a227">Maria, Cluj</strong></p></div>'''
        }
    },
    {
        'id': 'fomo_stock',
        'subject': {'ro': '⚠️ 3 produse au rămas din ultimul drop', 'en': '⚠️ Only 3 items left from the last drop'},
        'heading': {'ro': 'Se Termină.', 'en': 'Almost Gone.'},
        'body': {
            'ro': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Modelele din <strong style="color:#fff">ultimul drop</strong> se termină. Câteva au rămas pe stoc — <strong style="color:#c9a227">literalmente ultimele bucăți</strong>.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Data trecută au plecat în <strong style="color:#fff">48 de ore</strong>. De data asta probabil mai repede.</p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0;font-size:28px">⚠️</p>
            <p style="margin:8px 0 0;color:#c9a227;font-size:18px;font-weight:800;letter-spacing:2px">STOC LIMITAT</p>
            <p style="margin:8px 0 0;color:#999;font-size:13px">Când se termină, nu revin curând</p></div>''',
            'en': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Items from the <strong style="color:#fff">last drop</strong> are running out. A few left in stock — <strong style="color:#c9a227">literally the last pieces</strong>.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Last time they sold out in <strong style="color:#fff">48 hours</strong>. This time probably faster.</p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0;font-size:28px">⚠️</p>
            <p style="margin:8px 0 0;color:#c9a227;font-size:18px;font-weight:800;letter-spacing:2px">LIMITED STOCK</p>
            <p style="margin:8px 0 0;color:#999;font-size:13px">Once gone, they won't be back soon</p></div>'''
        }
    },
    {
        'id': 'new_drops',
        'subject': {'ro': '🔥 Tocmai am adăugat modele noi — nu le rata!', 'en': '🔥 Just dropped new styles — don\'t miss out!'},
        'heading': {'ro': 'Fresh Drops!', 'en': 'Fresh Drops!'},
        'body': {
            'ro': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Produse noi tocmai au aterizat pe <strong style="color:#c9a227">vexoramaison.com</strong>! 🔥</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Adidași, seturi, geci — toate la calitate <strong style="color:#fff">1:1 premium</strong> și prețuri care nu te lasă fără bani de mâncare. 😏</p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0;font-size:28px">🔥</p>
            <p style="margin:8px 0 0;color:#c9a227;font-size:18px;font-weight:800;letter-spacing:2px">MODELE NOI PE SITE</p>
            <p style="margin:8px 0 0;color:#999;font-size:13px">Verifică înainte să se termine stocul</p></div>''',
            'en': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">New products just landed on <strong style="color:#c9a227">vexoramaison.com</strong>! 🔥</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Sneakers, sets, jackets — all at <strong style="color:#fff">1:1 premium quality</strong> and prices that won't break the bank. 😏</p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0;font-size:28px">🔥</p>
            <p style="margin:8px 0 0;color:#c9a227;font-size:18px;font-weight:800;letter-spacing:2px">NEW STYLES ON SITE</p>
            <p style="margin:8px 0 0;color:#999;font-size:13px">Check them before stock runs out</p></div>'''
        }
    },
    {
        'id': 'restock_alert',
        'subject': {'ro': '🚨 Restock — Modelele epuizate sunt ÎNAPOI!', 'en': '🚨 Restock — Sold out items are BACK!'},
        'heading': {'ro': 'Sunt Înapoi!', 'en': 'They\'re Back!'},
        'body': {
            'ro': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Ți-a scăpat data trecută? <strong style="color:#c9a227">Azi e ziua ta.</strong></p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Cele mai cerute modele care s-au <strong style="color:#fff">epuizat instant</strong> sunt din nou disponibile. Dar stocul e limitat — și știi cum se termină.</p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0;font-size:28px">🚨</p>
            <p style="margin:8px 0 0;color:#c9a227;font-size:18px;font-weight:800;letter-spacing:2px">BACK IN STOCK</p>
            <p style="margin:8px 0 0;color:#999;font-size:13px">Nu rata din nou — ultima restock din sezon</p></div>''',
            'en': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Missed out last time? <strong style="color:#c9a227">Today's your day.</strong></p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">The most requested items that <strong style="color:#fff">sold out instantly</strong> are back. But stock is limited — and you know how fast they go.</p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0;font-size:28px">🚨</p>
            <p style="margin:8px 0 0;color:#c9a227;font-size:18px;font-weight:800;letter-spacing:2px">BACK IN STOCK</p>
            <p style="margin:8px 0 0;color:#999;font-size:13px">Don't miss again — last restock this season</p></div>'''
        }
    },
    {
        'id': 'comparison',
        'subject': {'ro': 'Tu vs. Prietenul care a descoperit Vexora 😏', 'en': 'You vs. Your friend who discovered Vexora 😏'},
        'heading': {'ro': 'Spot The Difference.', 'en': 'Spot The Difference.'},
        'body': {
            'ro': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Doi prieteni. Aceleași haine. <strong style="color:#c9a227">Prețuri complet diferite.</strong></p>
            <table cellpadding="0" cellspacing="0" width="100%" style="margin:0 0 24px">
            <tr><td style="width:48%;background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:18px;text-align:center;vertical-align:top">
            <p style="margin:0 0 8px;font-size:24px">😰</p>
            <p style="margin:0 0 6px;color:#fff;font-size:14px;font-weight:700">Prietenul A</p>
            <p style="margin:0 0 4px;color:#999;font-size:12px">Jordan 4 — <strong style="color:#ef4444">450€</strong></p>
            <p style="margin:0 0 4px;color:#999;font-size:12px">Dior Set — <strong style="color:#ef4444">1200€</strong></p>
            <p style="margin:0;color:#999;font-size:12px">LV Trainer — <strong style="color:#ef4444">890€</strong></p>
            <p style="margin:12px 0 0;color:#ef4444;font-size:16px;font-weight:800">TOTAL: 2540€</p>
            </td><td style="width:4%"></td>
            <td style="width:48%;background-color:#1a1014;border:1px solid #c9a227;border-radius:10px;padding:18px;text-align:center;vertical-align:top">
            <p style="margin:0 0 8px;font-size:24px">😎</p>
            <p style="margin:0 0 6px;color:#c9a227;font-size:14px;font-weight:700">Prietenul B (Vexora)</p>
            <p style="margin:0 0 4px;color:#999;font-size:12px">Jordan 4 — <strong style="color:#22c55e">84.99€</strong></p>
            <p style="margin:0 0 4px;color:#999;font-size:12px">Dior Set — <strong style="color:#22c55e">74.99€</strong></p>
            <p style="margin:0;color:#999;font-size:12px">LV Trainer — <strong style="color:#22c55e">84.99€</strong></p>
            <p style="margin:12px 0 0;color:#22c55e;font-size:16px;font-weight:800">TOTAL: 244.97€</p>
            </td></tr></table>
            <p style="color:#ccc;font-size:15px;text-align:center;margin:0"><strong style="color:#c9a227">Aceeași calitate. Nimeni nu vede diferența.</strong></p>''',
            'en': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Two friends. Same clothes. <strong style="color:#c9a227">Completely different prices.</strong></p>
            <table cellpadding="0" cellspacing="0" width="100%" style="margin:0 0 24px">
            <tr><td style="width:48%;background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:18px;text-align:center;vertical-align:top">
            <p style="margin:0 0 8px;font-size:24px">😰</p>
            <p style="margin:0 0 6px;color:#fff;font-size:14px;font-weight:700">Friend A</p>
            <p style="margin:0 0 4px;color:#999;font-size:12px">Jordan 4 — <strong style="color:#ef4444">450€</strong></p>
            <p style="margin:0 0 4px;color:#999;font-size:12px">Dior Set — <strong style="color:#ef4444">1200€</strong></p>
            <p style="margin:0;color:#999;font-size:12px">LV Trainer — <strong style="color:#ef4444">890€</strong></p>
            <p style="margin:12px 0 0;color:#ef4444;font-size:16px;font-weight:800">TOTAL: 2540€</p>
            </td><td style="width:4%"></td>
            <td style="width:48%;background-color:#1a1014;border:1px solid #c9a227;border-radius:10px;padding:18px;text-align:center;vertical-align:top">
            <p style="margin:0 0 8px;font-size:24px">😎</p>
            <p style="margin:0 0 6px;color:#c9a227;font-size:14px;font-weight:700">Friend B (Vexora)</p>
            <p style="margin:0 0 4px;color:#999;font-size:12px">Jordan 4 — <strong style="color:#22c55e">84.99€</strong></p>
            <p style="margin:0 0 4px;color:#999;font-size:12px">Dior Set — <strong style="color:#22c55e">74.99€</strong></p>
            <p style="margin:0;color:#999;font-size:12px">LV Trainer — <strong style="color:#22c55e">84.99€</strong></p>
            <p style="margin:12px 0 0;color:#22c55e;font-size:16px;font-weight:800">TOTAL: 244.97€</p>
            </td></tr></table>
            <p style="color:#ccc;font-size:15px;text-align:center;margin:0"><strong style="color:#c9a227">Same quality. Nobody sees the difference.</strong></p>'''
        }
    },
    {
        'id': 'free_shipping',
        'subject': {'ro': '🚚 Transport GRATUIT + Livrare Rapidă', 'en': '🚚 FREE Shipping + Fast Delivery'},
        'heading': {'ro': 'Zero Cost Livrare.', 'en': 'Zero Shipping Cost.'},
        'body': {
            'ro': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Știai că <strong style="color:#c9a227">toate comenzile</strong> de pe Vexora Maison au transport gratuit?</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Fără comandă minimă. Fără taxe ascunse. Pachetul ajunge la tine în <strong style="color:#fff">rapidă</strong>.</p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0;font-size:28px">🚚</p>
            <p style="margin:8px 0 0;color:#c9a227;font-size:18px;font-weight:800;letter-spacing:2px">TRANSPORT GRATUIT</p>
            <p style="margin:8px 0 0;color:#999;font-size:13px">Pe orice comandă · Livrare rapidă · Retur ușor</p></div>''',
            'en': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Did you know <strong style="color:#c9a227">all orders</strong> from Vexora Maison have free shipping?</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">No minimum order. No hidden fees. Your package arrives in <strong style="color:#fff">fast</strong>.</p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0;font-size:28px">🚚</p>
            <p style="margin:8px 0 0;color:#c9a227;font-size:18px;font-weight:800;letter-spacing:2px">FREE SHIPPING</p>
            <p style="margin:8px 0 0;color:#999;font-size:13px">All orders · fast delivery · easy returns</p></div>'''
        }
    },
    {
        'id': 'sneaker_game',
        'subject': {'ro': 'Sneaker game-ul tău e slab? Hai să-l fixăm. 👟', 'en': 'Your sneaker game is weak? Let\'s fix that. 👟'},
        'heading': {'ro': 'Level Up.', 'en': 'Level Up.'},
        'body': {
            'ro': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Jordan 4. Dunk Low. LV Trainer. Balenciaga Track.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Cele mai wanted modele din 2024-2025, toate pe <strong style="color:#c9a227">vexoramaison.com</strong> la prețuri de <strong style="color:#fff">sub 90€</strong>.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Calitate 1:1 · Box inclus · Livrare gratuită 🔥</p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0;font-size:28px">👟</p>
            <p style="margin:8px 0 0;color:#c9a227;font-size:18px;font-weight:800;letter-spacing:2px">SNEAKER COLLECTION</p>
            <p style="margin:8px 0 0;color:#999;font-size:13px">Jordan · Nike · LV · Balenciaga · De la 84.99€</p></div>''',
            'en': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Jordan 4. Dunk Low. LV Trainer. Balenciaga Track.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">The most wanted models of 2024-2025, all on <strong style="color:#c9a227">vexoramaison.com</strong> for <strong style="color:#fff">under 90€</strong>.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">1:1 quality · Box included · Free shipping 🔥</p>
            <div style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0;font-size:28px">👟</p>
            <p style="margin:8px 0 0;color:#c9a227;font-size:18px;font-weight:800;letter-spacing:2px">SNEAKER COLLECTION</p>
            <p style="margin:8px 0 0;color:#999;font-size:13px">Jordan · Nike · LV · Balenciaga · From 84.99€</p></div>'''
        }
    },
    {
        'id': 'vip_exclusive',
        'subject': {'ro': '🔒 Ofertă exclusivă pentru abonați — nu o rata', 'en': '🔒 Exclusive subscriber offer — don\'t miss it'},
        'heading': {'ro': 'Doar Pentru Tine.', 'en': 'Just For You.'},
        'body': {
            'ro': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Acest email e <strong style="color:#c9a227">doar pentru abonați</strong>. Nu e pe site, nu e pe Instagram.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Folosește codul <strong style="color:#fff">@VEXORAMAISON-ON-IG</strong> pentru 3% reducere la orice comandă. Plus transport gratuit. Plus livrare rapidă.</p>
            <div style="background-color:#1a1014;border:2px dashed #3d2a1a;border-radius:14px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0 0 6px;color:#666;font-size:10px;font-weight:700;letter-spacing:3px">CODUL TĂU VIP</p>
            <p style="margin:0;color:#c9a227;font-size:28px;font-weight:800;letter-spacing:4px;font-family:Courier New,monospace">@VEXORAMAISON-ON-IG</p>
            <p style="margin:10px 0 0;color:#999;font-size:12px">3% OFF · Toate produsele · Fără limită</p></div>''',
            'en': '''<p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">This email is <strong style="color:#c9a227">subscribers only</strong>. Not on the site, not on Instagram.</p>
            <p style="color:#ccc;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Use code <strong style="color:#fff">@VEXORAMAISON-ON-IG</strong> for 3% off any order. Plus free shipping. Plus fast delivery.</p>
            <div style="background-color:#1a1014;border:2px dashed #3d2a1a;border-radius:14px;padding:25px;text-align:center;margin:20px 0">
            <p style="margin:0 0 6px;color:#666;font-size:10px;font-weight:700;letter-spacing:3px">YOUR VIP CODE</p>
            <p style="margin:0;color:#c9a227;font-size:28px;font-weight:800;letter-spacing:4px;font-family:Courier New,monospace">@VEXORAMAISON-ON-IG</p>
            <p style="margin:10px 0 0;color:#999;font-size:12px">3% OFF · All products · No limit</p></div>'''
        }
    },
]

def get_subscriber_lang(email):
    try:
        db = get_db()
        row = db.execute("SELECT language FROM subscribers WHERE email=?", (email,)).fetchone()
        db.close()
        if row and row['language']:
            return row['language']
    except:
        pass
    # Fallback: check email domain
    if email.endswith('.ro'):
        return 'ro'
    return 'ro'  # Default Romanian

def pick_newsletter_template(exclude_ids=None):
    available = [t for t in NEWSLETTER_TEMPLATES if not exclude_ids or t['id'] not in exclude_ids]
    if not available:
        available = NEWSLETTER_TEMPLATES
    return random.choice(available)

def send_newsletter_bulk(template_id=None, custom_subject=None, custom_body=None):
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS subscribers(id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, language TEXT DEFAULT 'ro', subscribed_at TEXT, status TEXT DEFAULT 'active')''')
    db.execute('''CREATE TABLE IF NOT EXISTS newsletter_log(id INTEGER PRIMARY KEY AUTOINCREMENT, template_id TEXT, subject TEXT, sent_at TEXT, recipients INTEGER, status TEXT)''')
    subs = db.execute("SELECT email, language FROM subscribers WHERE status='active'").fetchall()
    if not subs:
        db.close()
        return 0
    # Get recent sent template IDs
    recent = db.execute("SELECT template_id FROM newsletter_log ORDER BY sent_at DESC LIMIT 3").fetchall()
    recent_ids = [r['template_id'] for r in recent]
    
    if custom_subject and custom_body:
        tpl_id = 'custom_' + datetime.datetime.now().strftime('%Y%m%d%H%M')
        subject = custom_subject
        body = custom_body
        heading = 'Vexora Maison'
    else:
        tpl = pick_newsletter_template(recent_ids) if not template_id else next((t for t in NEWSLETTER_TEMPLATES if t['id'] == template_id), pick_newsletter_template(recent_ids))
        tpl_id = tpl['id']
        subject = tpl['subject']['ro']
        heading = tpl['heading']['ro']
        body = tpl['body']['ro']
    
    sent = 0
    for s in subs:
        email = s['email']
        lang = s['language'] if 'language' in s.keys() else get_subscriber_lang(email)
        if not custom_subject:
            tpl = next((t for t in NEWSLETTER_TEMPLATES if t['id'] == tpl_id), NEWSLETTER_TEMPLATES[0])
            subj = tpl['subject'].get(lang, tpl['subject']['ro'])
            hdng = tpl['heading'].get(lang, tpl['heading']['ro'])
            bdy = tpl['body'].get(lang, tpl['body']['ro'])
        else:
            subj = subject
            hdng = heading
            bdy = body
        
        unsub = f'<p style="margin:20px 0 0;text-align:center;font-size:11px;color:#555">Nu mai doriți să primiți emailuri? <a href="{RAILWAY_URL}/unsubscribe?email={urllib.parse.quote(email)}" style="color:#888">Dezabonare</a></p>'
        full_body = bdy + unsub
        if send_email(email, subj, email_template('VEXORA MAISON', hdng, full_body, 'SHOP NOW', SITE_URL)):
            sent += 1
    
    now = datetime.datetime.now().isoformat()
    db.execute('INSERT INTO newsletter_log(template_id, subject, sent_at, recipients, status) VALUES(?,?,?,?,?)',
               (tpl_id, subject, now, sent, 'sent'))
    db.commit()
    db.close()
    print(f'Newsletter sent: {tpl_id} to {sent} subscribers')
    return sent

STATUSES = [
    {'key': 'new', 'label': 'New Order', 'icon': '📥', 'color': '#3b82f6'},
    {'key': 'ordered', 'label': 'Ordered on Agent', 'icon': '🛒', 'color': '#f59e0b'},
    {'key': 'warehouse', 'label': 'In Warehouse', 'icon': '📦', 'color': '#8b5cf6'},
    {'key': 'shipped_china', 'label': 'Shipped from China', 'icon': '✈️', 'color': '#06b6d4'},
    {'key': 'in_romania', 'label': 'Arrived in Romania', 'icon': '🇷🇴', 'color': '#10b981'},
    {'key': 'sent_cargus', 'label': 'Sent with Cargus', 'icon': '🚚', 'color': '#f97316'},
    {'key': 'delivered', 'label': 'Delivered', 'icon': '✅', 'color': '#22c55e'},
    {'key': 'cancelled', 'label': 'Cancelled', 'icon': '❌', 'color': '#ef4444'}
]

# Status-specific email content
STATUS_MESSAGES = {
    'new': {'subject': 'Order Confirmed!', 'heading': 'Order Confirmed!', 'body': 'We\'ve received your order and it\'s being processed. We\'ll keep you updated every step of the way.'},
    'ordered': {'subject': 'Your Order Has Been Placed!', 'heading': 'Ordered on Agent', 'body': 'Great news! Your product has been ordered from our supplier. It will be prepared and shipped soon.'},
    'warehouse': {'subject': 'Your Product is Ready!', 'heading': 'In Warehouse', 'body': 'Your product is now in our warehouse and being prepared for international shipping.'},
    'shipped_china': {'subject': 'Your Order is on its Way!', 'heading': 'Shipped from China', 'body': 'Your order has been shipped internationally! It\'s on its way to Romania. This usually takes 7-14 days.'},
    'in_romania': {'subject': 'Your Order Arrived in Romania!', 'heading': 'Arrived in Romania', 'body': 'Great news — your order has arrived in Romania! We\'re preparing it for local delivery with Cargus.'},
    'sent_cargus': {'subject': 'Out for Delivery!', 'heading': 'Sent with Cargus', 'body': 'Your order is on its way to you via Cargus! You should receive it within 1-2 business days.'},
    'delivered': {'subject': 'Order Delivered!', 'heading': 'Delivered', 'body': 'Your order has been delivered! We hope you love your new product. Don\'t forget to share it on Instagram and tag us!'},
    'cancelled': {'subject': 'Order Cancelled', 'heading': 'Cancelled', 'body': 'Your order has been cancelled. If you have any questions, don\'t hesitate to reach out to us.'},
}

def _sqlite_to_pg(sql):
    """Convert SQLite SQL to PostgreSQL compatible SQL"""
    sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
    sql = sql.replace('?', '%s')
    # IF NOT EXISTS works in both
    return sql

class PgRowWrapper:
    """Makes psycopg2 DictRow behave like sqlite3.Row for safe_get compatibility"""
    def __init__(self, row, cursor):
        self._row = row
        self._cursor = cursor
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._row[key]
        return self._row[key]
    def keys(self):
        return self._row.keys() if hasattr(self._row, 'keys') else []

class PgCursorWrapper:
    """Wraps psycopg2 cursor to convert ? to %s and return compatible rows"""
    def __init__(self, conn):
        self._conn = conn
        self._cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    def execute(self, sql, params=None):
        sql = _sqlite_to_pg(sql)
        if params:
            self._cursor.execute(sql, params)
        else:
            self._cursor.execute(sql)
        return self
    def fetchone(self):
        row = self._cursor.fetchone()
        return row
    def fetchall(self):
        return self._cursor.fetchall()
    def commit(self):
        self._conn.commit()
    def close(self):
        self._cursor.close()
        self._conn.close()
    @property
    def row_factory(self):
        return None
    @row_factory.setter
    def row_factory(self, val):
        pass  # ignore — we always use DictCursor

def get_db():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        db = PgCursorWrapper(conn)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        db = conn

    # Create tables
    db.execute('''CREATE TABLE IF NOT EXISTS orders(
        id SERIAL PRIMARY KEY, order_id TEXT, order_number TEXT,
        product_name TEXT, product_url TEXT, customer_email TEXT,
        shipping_name TEXT, shipping_address TEXT, shipping_city TEXT,
        shipping_zip TEXT, shipping_phone TEXT, total TEXT, currency TEXT,
        status TEXT DEFAULT 'new', tracking_number TEXT DEFAULT '',
        tracking_carrier TEXT DEFAULT '', tracking_url TEXT DEFAULT '',
        created_at TEXT, updated_at TEXT, timeline TEXT DEFAULT '[]',
        product_image TEXT DEFAULT '')''')
    db.execute('''CREATE TABLE IF NOT EXISTS messages(
        id SERIAL PRIMARY KEY, name TEXT, email TEXT,
        subject TEXT, order_number TEXT, message TEXT,
        status TEXT DEFAULT 'new', created_at TEXT,
        replies TEXT DEFAULT '[]')''')
    db.execute('''CREATE TABLE IF NOT EXISTS subscribers(
        id SERIAL PRIMARY KEY, email TEXT UNIQUE,
        language TEXT DEFAULT 'ro', subscribed_at TEXT,
        status TEXT DEFAULT 'active')''')
    db.execute('''CREATE TABLE IF NOT EXISTS newsletter_log(
        id SERIAL PRIMARY KEY, template_id TEXT, subject TEXT,
        sent_at TEXT, recipients INTEGER, status TEXT)''')
    db.commit()
    return db

def safe_get(row, key, default=''):
    try:
        return row[key] if row[key] is not None else default
    except (IndexError, KeyError):
        return default

def send_email(to, subject, html):
    if not RESEND_KEY:
        print('RESEND_API_KEY not set')
        return False
    try:
        unsub_url = f'{RAILWAY_URL}/unsubscribe?email={urllib.parse.quote(to)}'
        r = requests.post('https://api.resend.com/emails', headers={
            'Authorization': f'Bearer {RESEND_KEY}',
            'Content-Type': 'application/json'
        }, json={
            'from': FROM_EMAIL,
            'to': [to],
            'reply_to': REPLY_TO,
            'subject': subject,
            'html': html,
            'headers': {
                'List-Unsubscribe': f'<{unsub_url}>',
                'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
                'X-Entity-Ref-ID': hashlib.md5(f'{to}{subject}{datetime.datetime.now().isoformat()}'.encode()).hexdigest()
            }
        }, timeout=10)
        if r.status_code in [200, 201]:
            print(f'Email sent to {to}')
            return True
        else:
            print(f'Email error {r.status_code}: {r.text}')
            return False
    except Exception as e:
        print(f'Email exception: {e}')
        return False

def email_template(title, heading, body_html, button_text='', button_url='', show_social=True):
    button_block = ''
    if button_text and button_url:
        button_block = f'''<tr><td style="padding:35px 0 5px" align="center">
            <a href="{button_url}" style="display:inline-block;padding:16px 48px;background-color:#c9a227;color:#1a0a0e;text-decoration:none;border-radius:8px;font-family:Helvetica,sans-serif;font-size:13px;font-weight:800;letter-spacing:2px;text-transform:uppercase">{button_text}</a></td></tr>'''
    social_block = ''
    if show_social:
        social_block = '<tr><td style="padding:20px 0 0" align="center">' + \
            '<table cellpadding="0" cellspacing="0"><tr>' + \
            '<td style="padding:0 12px"><a href="https://instagram.com/vexoramaison" style="color:#bbbbbb;text-decoration:none;font-family:Helvetica,sans-serif;font-size:12px;letter-spacing:1px">&#x1F4F8; INSTAGRAM</a></td>' + \
            '<td style="color:#555;font-size:10px">&#8226;</td>' + \
            '<td style="padding:0 12px"><a href="https://www.tiktok.com/@vexoramaison" style="color:#bbbbbb;text-decoration:none;font-family:Helvetica,sans-serif;font-size:12px;letter-spacing:1px">&#x1F3B5; TIKTOK</a></td>' + \
            '<td style="color:#555;font-size:10px">&#8226;</td>' + \
            '<td style="padding:0 12px"><a href="https://wa.me/40748460032" style="color:#bbbbbb;text-decoration:none;font-family:Helvetica,sans-serif;font-size:12px;letter-spacing:1px">&#x1F4AC; WHATSAPP</a></td>' + \
            '<td style="color:#555;font-size:10px">&#8226;</td>' + \
            '<td style="padding:0 12px"><a href="' + SITE_URL + '" style="color:#bbbbbb;text-decoration:none;font-family:Helvetica,sans-serif;font-size:12px;letter-spacing:1px">&#x1F6CD; SHOP</a></td>' + \
            '</tr></table></td></tr>'
    return f'''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="color-scheme" content="dark light">
<meta name="supported-color-schemes" content="dark light">
<style>
:root{{color-scheme:dark light}}
body,table,td{{font-family:Helvetica,Arial,sans-serif}}
@media only screen and (max-width:620px){{
.ec{{width:100%!important;border-radius:0!important}}
.eb{{padding:28px 20px!important}}
.eh{{padding:24px 20px 18px!important}}
.ef{{padding:20px!important}}
.ew{{padding:0!important}}
}}
</style></head>
<body style="margin:0;padding:0;background-color:#080305;font-family:Helvetica,Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" bgcolor="#080305" class="ew" style="background-color:#080305;padding:40px 10px">
<tr><td align="center" bgcolor="#080305">
<table width="600" cellpadding="0" cellspacing="0" bgcolor="#120810" class="ec" style="background-color:#120810;border-radius:16px;overflow:hidden;max-width:600px;width:100%">
<tr><td class="eh" bgcolor="#1a0f14" style="background-color:#1a0f14;padding:35px 30px 25px;text-align:center;border-bottom:1px solid #261a1e">
<img src="https://cdn.shopify.com/s/files/1/1013/0466/4412/files/cropped_circle_image.png?v=1774793294" alt="Vexora Maison" width="80" height="80" style="border-radius:50%;border:2px solid #3d2a1a;display:block;margin:0 auto">
<p style="margin:14px 0 0;color:#c9a227;font-size:13px;font-weight:700;letter-spacing:5px;text-transform:uppercase;text-shadow:0 2px 4px rgba(0,0,0,.7),0 0 16px rgba(201,162,39,.3)">{title}</p>
</td></tr>
<tr><td class="eb" bgcolor="#120810" style="padding:40px 36px 30px;background-color:#120810">
<h1 style="margin:0 0 8px;font-size:26px;color:#ffffff;text-align:center;font-weight:700;letter-spacing:0.5px;text-shadow:0 2px 4px rgba(0,0,0,.5),0 0 12px rgba(201,162,39,.15)">{heading}</h1>
<table width="60" cellpadding="0" cellspacing="0" style="margin:0 auto 30px" align="center"><tr><td bgcolor="#c9a227" style="height:3px;background-color:#c9a227;font-size:0;line-height:0;box-shadow:0 0 8px rgba(201,162,39,.4)">&nbsp;</td></tr></table>
{body_html}
{button_block}
</td></tr>
<tr><td class="ef" bgcolor="#0a0507" style="background-color:#0a0507;padding:28px 36px;border-top:1px solid #1a1015">
{social_block}
<tr><td style="padding:12px 0 0" align="center">
<p style="margin:0;color:#aaaaaa;font-size:11px;letter-spacing:0.5px">&copy; 2022 Vexora Maison</p>
<p style="margin:5px 0 0"><a href="{SITE_URL}" style="color:#999999;text-decoration:none;font-size:11px">vexoramaison.com</a></p>
</td></tr>
</td></tr>
</table>
</td></tr></table></body></html>'''

def cors_response(data, status=200):
    resp = make_response(jsonify(data), status)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    return resp

# ===================== HEALTH =====================
@app.route('/health')
def health():
    db = get_db()
    oc = db.execute('SELECT COUNT(*) as cnt FROM orders').fetchone()['cnt']
    mc = db.execute('SELECT COUNT(*) as cnt FROM messages').fetchone()['cnt']
    db.execute('''CREATE TABLE IF NOT EXISTS subscribers(
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE,
        subscribed_at TEXT, status TEXT DEFAULT 'active')''')
    sc = db.execute('SELECT COUNT(*) as cnt FROM subscribers').fetchone()['cnt']
    db.close()
    return jsonify({'status': 'online', 'orders': oc, 'messages': mc, 'subscribers': sc})

# ===================== SUBSCRIBE API =====================
@app.route('/api/subscribe', methods=['POST', 'OPTIONS'])
def api_subscribe():
    if request.method == 'OPTIONS':
        return cors_response({})
    try:
        d = request.get_json()
        email = d.get('email', '').strip()
        lang = d.get('language', 'ro').strip()
        if lang not in ('ro', 'en'):
            lang = 'ro'
        if not email or '@' not in email:
            return cors_response({'success': False, 'error': 'Invalid email'})
        
        now = datetime.datetime.now().isoformat()
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS subscribers(
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE,
            language TEXT DEFAULT 'ro', subscribed_at TEXT, status TEXT DEFAULT 'active')''')
        # Add language column if missing (migration)
        try: db.execute("ALTER TABLE subscribers ADD COLUMN language TEXT DEFAULT 'ro'")
        except: pass
        try:
            db.execute('INSERT INTO subscribers(email, language, subscribed_at) VALUES(?,?,?)', (email, lang, now))
            db.commit()
        except:
            # Already exists — update language
            db.execute('UPDATE subscribers SET language=?, status="active" WHERE email=?', (lang, email))
            db.commit()
            db.close()
            return cors_response({'success': True, 'message': 'Already subscribed'})
        db.close()

        # Send bilingual welcome email
        if lang == 'ro':
            subj = 'Bine ai venit la Vexora Maison — Ai 3% REDUCERE!'
            heading = 'Bine Ai Venit!'
            body_html = f'''<p style="color:#bbb;font-size:15px;line-height:1.7;margin:0 0 24px;text-align:center">Bine ai venit în familia Vexora Maison! 🎉</p>
            <p style="color:#999;font-size:14px;line-height:1.6;margin:0 0 28px;text-align:center">Mulțumim că te-ai abonat. Iată codul tău exclusiv de <strong style="color:#c9a227">3% reducere</strong> la prima comandă:</p>
            <table cellpadding="0" cellspacing="0" width="100%" style="background-color:#1a1014;border:2px dashed #3d2a1a;border-radius:14px;margin:0 0 28px">
            <tr><td style="padding:32px 24px;text-align:center">
            <p style="margin:0 0 10px;color:#666;font-size:10px;font-weight:700;letter-spacing:3px">CODUL TĂU DE REDUCERE</p>
            <p style="margin:0;color:#c9a227;font-size:32px;font-weight:800;letter-spacing:5px;font-family:'Courier New',monospace">@VEXORAMAISON-ON-IG</p>
            <p style="margin:12px 0 0;color:#999;font-size:12px">Valabil pe toate produsele · Fără comandă minimă</p>
            </td></tr></table>
            <p style="color:#999;font-size:14px;line-height:1.6;margin:0 0 16px;text-align:center">Ca abonat, vei primi:</p>
            <table cellpadding="0" cellspacing="0" width="100%" style="background-color:#150b0f;border:1px solid #221519;border-radius:10px;margin:0 0 8px">
            <tr><td style="padding:6px 18px;color:#bbb;font-size:13px;border-bottom:1px solid #1a1015">✨ Acces anticipat la produse noi & restocuri</td></tr>
            <tr><td style="padding:6px 18px;color:#bbb;font-size:13px;border-bottom:1px solid #1a1015">🏷️ Reduceri exclusive pentru abonați</td></tr>
            <tr><td style="padding:6px 18px;color:#bbb;font-size:13px;border-bottom:1px solid #1a1015">📦 Prioritate în livrare</td></tr>
            <tr><td style="padding:6px 18px;color:#bbb;font-size:13px">🔔 Fii primul care află despre oferte</td></tr>
            </table>'''
            btn_text = 'CUMPĂRĂ CU 3% REDUCERE'
        else:
            subj = 'Welcome to Vexora Maison — Here\'s your 3% OFF!'
            heading = 'Welcome to the Family!'
            body_html = f'''<p style="color:#bbb;font-size:15px;line-height:1.7;margin:0 0 24px;text-align:center">Welcome to the Vexora Maison family! 🎉</p>
            <p style="color:#999;font-size:14px;line-height:1.6;margin:0 0 28px;text-align:center">Thank you for subscribing. Here's your exclusive <strong style="color:#c9a227">3% discount</strong> on your first order:</p>
            <table cellpadding="0" cellspacing="0" width="100%" style="background-color:#1a1014;border:2px dashed #3d2a1a;border-radius:14px;margin:0 0 28px">
            <tr><td style="padding:32px 24px;text-align:center">
            <p style="margin:0 0 10px;color:#666;font-size:10px;font-weight:700;letter-spacing:3px">YOUR DISCOUNT CODE</p>
            <p style="margin:0;color:#c9a227;font-size:32px;font-weight:800;letter-spacing:5px;font-family:'Courier New',monospace">@VEXORAMAISON-ON-IG</p>
            <p style="margin:12px 0 0;color:#999;font-size:12px">Valid on all products · No minimum order</p>
            </td></tr></table>
            <p style="color:#999;font-size:14px;line-height:1.6;margin:0 0 16px;text-align:center">As a subscriber, you'll get:</p>
            <table cellpadding="0" cellspacing="0" width="100%" style="background-color:#150b0f;border:1px solid #221519;border-radius:10px;margin:0 0 8px">
            <tr><td style="padding:6px 18px;color:#bbb;font-size:13px;border-bottom:1px solid #1a1015">✨ Early access to new drops &amp; restocks</td></tr>
            <tr><td style="padding:6px 18px;color:#bbb;font-size:13px;border-bottom:1px solid #1a1015">🏷️ Exclusive subscriber-only discounts</td></tr>
            <tr><td style="padding:6px 18px;color:#bbb;font-size:13px;border-bottom:1px solid #1a1015">📦 Priority shipping on your orders</td></tr>
            <tr><td style="padding:6px 18px;color:#bbb;font-size:13px">🔔 Be the first to know about sales</td></tr>
            </table>'''
            btn_text = 'SHOP NOW WITH 3% OFF'
        
        send_email(email, subj, email_template('VEXORA MAISON', heading, body_html, btn_text, SITE_URL))
        print(f'New subscriber: {email} ({lang})')
        return cors_response({'success': True})
    except Exception as e:
        print(f'Subscribe error: {e}')
        return cors_response({'success': False, 'error': str(e)})

# ===================== CONTACT API =====================
@app.route('/api/contact', methods=['POST', 'OPTIONS'])
def api_contact():
    if request.method == 'OPTIONS':
        return cors_response({})
    try:
        d = request.get_json()
        name = d.get('name', '').strip()
        email = d.get('email', '').strip()
        subject = d.get('subject', '').strip()
        order_number = d.get('order_number', '').strip()
        message = d.get('message', '').strip()
        if not name or not email or not subject or not message:
            return cors_response({'success': False, 'error': 'All fields are required'})
        now = datetime.datetime.now().isoformat()
        db = get_db()
        db.execute('INSERT INTO messages(name,email,subject,order_number,message,status,created_at,replies) VALUES(?,?,?,?,?,?,?,?)',
                   (name, email, subject, order_number, message, 'new', now, '[]'))
        db.commit()
        db.close()
        # Send confirmation email to customer
        body_html = f'''<p style="color:#bbbbbb !important;font-size:15px;line-height:1.7;margin:0 0 24px">Hi <strong style="color:#fff">{name}</strong>,</p>
        <p style="color:#999999 !important;font-size:14px;line-height:1.6;margin:0 0 28px">Thank you for contacting Vexora Maison! We've received your message and will get back to you within <strong style="color:#c9a227">24 hours</strong>.</p>
        <table cellpadding="0" cellspacing="0" width="100%" style="background-color:#1a1014 !important;border:1px solid #2a1a1e;border-radius:12px;margin:0 0 28px">
        <tr><td style="padding:20px 22px">
        <p style="margin:0 0 10px;color:#777777 !important;font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase">YOUR MESSAGE</p>
        <p style="margin:0 0 6px;color:#999999 !important;font-size:13px"><strong style="color:#fff">Subject:</strong> {subject}</p>
        {f'<p style="margin:0 0 6px;color:#999999 !important;font-size:13px"><strong style="color:#fff">Order:</strong> {order_number}</p>' if order_number else ''}
        <p style="margin:8px 0 0;color:#aaa;font-size:13px;line-height:1.6;white-space:pre-wrap;border-top:1px solid #221519;padding-top:10px">{message}</p>
        </td></tr></table>
        <table cellpadding="0" cellspacing="0" width="100%" style="background-color:#150b0f !important;border:1px solid #221519;border-radius:10px">
        <tr><td style="padding:16px 20px">
        <p style="margin:0 0 6px;color:#c9a227;font-size:12px;font-weight:700">Need a faster response?</p>
        <p style="margin:0;color:#999999 !important;font-size:12px;line-height:1.5">DM us on <a href="https://instagram.com/vexoramaison" style="color:#c9a227;font-weight:700;text-decoration:none">Instagram @vexoramaison</a> or message us on <a href="https://wa.me/40748460032" style="color:#c9a227;font-weight:700;text-decoration:none">WhatsApp</a> — we usually reply within 1-2 hours!</p>
        </td></tr></table>'''
        send_email(email, f'We received your message — {subject}', email_template('VEXORA MAISON', 'Message Received!', body_html, 'VISIT OUR STORE', SITE_URL))
        # Send notification to admin
        admin_body = f'''<p style="color:#ccc;font-size:15px;line-height:1.7">New contact message from <strong style="color:#c9a227">{name}</strong> ({email})</p>
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#1a1014 !important;border:1px solid #2a1a1e;border-radius:8px;margin:20px 0">
        <tr><td style="padding:20px">
        <p style="margin:0 0 5px;color:#999999 !important;font-size:13px"><strong style="color:#fff">Subject:</strong> {subject}</p>
        {f'<p style="margin:0 0 5px;color:#999999 !important;font-size:13px"><strong style="color:#fff">Order:</strong> {order_number}</p>' if order_number else ''}
        <p style="margin:10px 0 0;color:#aaa;font-size:13px;line-height:1.6;white-space:pre-wrap">{message}</p>
        </td></tr></table>'''
        send_email('support@vexoramaison.com', f'[Vexora Contact] {subject} — from {name}', email_template('NEW MESSAGE', f'From: {name}', admin_body, 'OPEN DASHBOARD', RAILWAY_URL + '/admin'))
        print(f'Contact: {name} ({email}) — {subject}')
        return cors_response({'success': True})
    except Exception as e:
        print(f'Contact error: {e}')
        return cors_response({'success': False, 'error': str(e)})

# ===================== WEBHOOK (WooCommerce orders) =====================
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        d = request.get_json()
        now = datetime.datetime.now().isoformat()
        
        # WooCommerce webhook format
        order_id = str(d.get('id', ''))
        order_number = str(d.get('number', d.get('id', '')))
        
        # Get customer info from billing
        billing = d.get('billing', {})
        shipping = d.get('shipping', {})
        
        customer_email = billing.get('email', '')
        shipping_name = f"{shipping.get('first_name', billing.get('first_name', ''))} {shipping.get('last_name', billing.get('last_name', ''))}".strip()
        shipping_address = shipping.get('address_1', billing.get('address_1', ''))
        shipping_city = shipping.get('city', billing.get('city', ''))
        shipping_zip = shipping.get('postcode', billing.get('postcode', ''))
        shipping_phone = billing.get('phone', '')
        
        # Get product info from line items
        line_items = d.get('line_items', [])
        product_names = [item.get('name', '') for item in line_items]
        product_name = ', '.join(product_names) if product_names else 'Unknown Product'
        product_url = line_items[0].get('sku', '') if line_items else ''
        product_image = ''
        if line_items and line_items[0].get('image'):
            product_image = line_items[0]['image'].get('src', '')
        
        total = d.get('total', '0')
        currency = d.get('currency', 'EUR')
        
        timeline = json.dumps([{'status': 'New Order', 'date': now, 'icon': '📥', 'color': '#3b82f6', 'note': 'Order received from WooCommerce'}])
        
        db = get_db()
        db.execute('INSERT INTO orders(order_id,order_number,product_name,product_url,product_image,customer_email,shipping_name,shipping_address,shipping_city,shipping_zip,shipping_phone,total,currency,status,created_at,updated_at,timeline) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (order_id, order_number, product_name, product_url, product_image,
                    customer_email, shipping_name, shipping_address,
                    shipping_city, shipping_zip, shipping_phone,
                    total, currency, 'new', now, now, timeline))
        db.commit()
        db.close()
        
        # Send order confirmation email
        try:
            size_info = ''
            for item in line_items:
                meta = item.get('meta_data', [])
                for m in meta:
                    if m.get('display_key', '').lower() in ['size', 'mărime', 'color', 'culoare']:
                        size_info += f" ({m.get('display_key')}: {m.get('display_value')})"
            
            body_html = f"""<p style="color:#aaa!important;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Hi <strong style="color:#fff">{shipping_name}</strong>,</p>
            <p style="color:#aaa!important;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">Thank you for your order! We've received it and it's being processed.</p>
            <table cellpadding="0" cellspacing="0" width="100%" style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;margin:0 0 24px">
            <tr><td style="padding:20px">
            <p style="margin:0 0 12px;color:#777!important;font-size:9px;font-weight:700;letter-spacing:3px;text-transform:uppercase">ORDER DETAILS</p>
            <table cellpadding="0" cellspacing="0" width="100%"><tr>
            {'<td style="width:90px;vertical-align:top;padding-right:16px"><a href="' + SITE_URL + '"><img src="' + product_image + '" alt="Product" width="90" height="90" style="width:90px;height:90px;object-fit:cover;border-radius:10px;border:1px solid #2a1a1e;display:block"></a></td>' if product_image else ''}
            <td style="vertical-align:middle">
            <p style="margin:0 0 6px;color:#fff;font-size:15px;font-weight:700;line-height:1.3">{product_name}{size_info}</p>
            <p style="margin:0 0 6px;color:#c9a227;font-size:11px;font-weight:700;letter-spacing:1px">ORDER #{order_number}</p>
            <p style="margin:0;color:#c9a227;font-size:18px;font-weight:800">{total} {currency}</p>
            </td></tr></table>
            </td></tr></table>
            <p style="color:#888!important;font-size:13px;line-height:1.6;text-align:center">We'll send you updates as your order progresses. Track your order anytime:</p>"""
            send_email(customer_email, f'Order #{order_number} Confirmed!', 
                       email_template('VEXORA MAISON', 'Order Confirmed!', body_html, 'TRACK YOUR ORDER', f'{SITE_URL}/track-your-order'))
        except Exception as e:
            print(f'Order confirmation email error: {e}')
        
        print(f'Order #{order_number} received from WooCommerce')
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        print(f'Webhook error: {e}')
        return jsonify({'error': str(e)}), 200

# ===================== TRACK API =====================
@app.route('/track')
def track():
    order = request.args.get('order', '').strip().replace('#', '')
    if not order:
        return cors_response({'error': 'Missing order number'}, 400)
    db = get_db()
    row = db.execute('SELECT * FROM orders WHERE order_number=?', (order,)).fetchone()
    db.close()
    if not row:
        resp = make_response(jsonify({'error': 'Order not found'}), 404)
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp
    s = next((x for x in STATUSES if x['key'] == safe_get(row,'status','new')), STATUSES[0])
    data = {
        'order_number': safe_get(row,'order_number'), 'status': safe_get(row,'status','new'),
        'status_label': s['label'], 'status_icon': s['icon'], 'status_color': s['color'],
        'product_name': safe_get(row,'product_name'), 'created_at': safe_get(row,'created_at'),
        'tracking_number': safe_get(row,'tracking_number'), 'tracking_carrier': safe_get(row,'tracking_carrier'),
        'tracking_url': safe_get(row,'tracking_url'), 'timeline': json.loads(safe_get(row,'timeline','[]')),
        'all_statuses': STATUSES
    }
    return cors_response(data)

# ===================== ADMIN DASHBOARD =====================
@app.route('/admin')
def admin():
    pw = request.args.get('pw', request.cookies.get('dpw', ''))
    if pw != DASH_PASS:
        return '''<html><body style="background:#0f0609;display:flex;align-items:center;justify-content:center;min-height:100vh;font-family:Helvetica,sans-serif">
        <form style="text-align:center"><h2 style="color:#c9a227;letter-spacing:3px;margin-bottom:20px">VEXORA ADMIN</h2>
        <input name="pw" type="password" placeholder="Password" style="padding:14px 20px;border-radius:8px;border:1px solid rgba(201,162,39,.3);background:#1a0a0e;color:#fff;font-size:14px;width:250px;outline:none">
        <br><br><button style="padding:12px 30px;background:#c9a227;color:#1a0a0e;border:none;border-radius:8px;font-weight:700;cursor:pointer;letter-spacing:1px">LOGIN</button></form></body></html>'''
    
    tab = request.args.get('tab', 'orders')
    db = get_db()
    orders = db.execute('SELECT * FROM orders ORDER BY created_at DESC').fetchall()
    messages = db.execute('SELECT * FROM messages ORDER BY created_at DESC').fetchall()
    db.execute('''CREATE TABLE IF NOT EXISTS subscribers(
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE,
        subscribed_at TEXT, status TEXT DEFAULT 'active')''')
    subscribers = db.execute('SELECT * FROM subscribers ORDER BY subscribed_at DESC').fetchall()
    db.close()

    # Count unread messages
    unread = sum(1 for m in messages if m['status'] == 'new')

    # Pre-fetch WooCommerce products for manual order form
    shopify_products_json = '[]'
    try:
        if WC_KEY and WC_SECRET:
            r = requests.get(f'{WC_URL}/wp-json/wc/v3/products', params={
                'consumer_key': WC_KEY, 'consumer_secret': WC_SECRET,
                'per_page': 100, 'status': 'publish'
            }, timeout=10)
            if r.status_code == 200:
                prods = r.json()
                prod_list = []
                for p in prods:
                    img = ''
                    images = p.get('images', [])
                    if images:
                        img = images[0].get('src', '')
                    price = p.get('price', '0')
                    try: price = f"{float(price):.2f}"
                    except: pass
                    prod_list.append({'t': p.get('name',''), 'i': img, 'p': price})
                shopify_products_json = json.dumps(prod_list)
    except Exception as e:
        print(f'WooCommerce products fetch: {e}')

    orders_html = ''
    for idx, o in enumerate(orders):
        s = next((x for x in STATUSES if x['key'] == safe_get(o,'status','new')), STATUSES[0])
        oid = o['id']
        trk = safe_get(o,'tracking_number')
        carrier = safe_get(o,'tracking_carrier')
        email = safe_get(o,'customer_email')
        timeline = json.loads(safe_get(o,'timeline','[]'))
        timeline_html = ''
        for t in timeline:
            timeline_html += f'<div style="display:flex;gap:8px;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.03)"><span style="font-size:16px">{t.get("icon","")}</span><span style="color:#ccc;font-size:12px;flex:1">{t.get("status","")}</span><span style="color:#666;font-size:11px">{t.get("date","")[:16]}</span></div>'
        
        orders_html += f'''<div style="background:#1a0e0e;border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:20px;margin-bottom:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
        <div style="display:flex;align-items:center;gap:12px">{'<img src="'+safe_get(o,"product_image")+'" style="width:50px;height:50px;object-fit:cover;border-radius:8px;border:1px solid #2a1a1e">' if safe_get(o,'product_image') else ''}<div><span style="color:#c9a227;font-size:22px;font-weight:800">#{safe_get(o,'order_number')}</span>
        <span style="color:#999999 !important;font-size:13px;margin-left:10px">{safe_get(o,'product_name')}</span></div></div>
        <span style="background:{s['color']}18;color:{s['color']};padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700">{s['icon']} {s['label']}</span></div>
        <div style="margin-top:10px;font-size:12px;color:#888">{email} | {safe_get(o,'shipping_name')} | {safe_get(o,'shipping_address')} {safe_get(o,'shipping_city')}</div>
        <div style="margin-top:4px;font-size:12px;color:#888">💰 {safe_get(o,'total')} {safe_get(o,'currency')} | 📅 {safe_get(o,'created_at','')[:10]}</div>
        {'<div style="margin-top:8px;font-size:12px"><span style=color:#c9a227;font-weight:700>📦 Tracking:</span> <span style=color:#ccc>'+trk+'</span> <span style=color:#888>('+carrier+')</span></div>' if trk else ''}
        
        <details style="margin-top:14px">
        <summary style="color:#c9a227;font-size:12px;font-weight:700;cursor:pointer;letter-spacing:1px;padding:8px 0">📋 TIMELINE ({len(timeline)} events)</summary>
        <div style="padding:10px 0">{timeline_html if timeline_html else '<p style=color:#555;font-size:12px>No events yet.</p>'}</div>
        </details>

        <details style="margin-top:10px">
        <summary style="color:#c9a227;font-size:12px;font-weight:700;cursor:pointer;letter-spacing:1px;padding:8px 0">✏️ UPDATE STATUS & SEND EMAIL</summary>
        <form action="/admin/update" method="POST" style="margin-top:10px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);border-radius:8px;padding:16px">
        <input type="hidden" name="pw" value="{pw}">
        <input type="hidden" name="id" value="{oid}">
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">
        <div style="flex:1;min-width:200px">
        <label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">TRACKING NUMBER</label>
        <input name="tracking" value="{trk}" placeholder="e.g. 1234567890" style="width:100%;padding:10px;border-radius:6px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#fff;font-size:13px;outline:none">
        </div>
        <div style="min-width:150px">
        <label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">CARRIER</label>
        <select name="carrier" style="width:100%;padding:10px;border-radius:6px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#fff;font-size:13px;outline:none">
        <option value="DHL" {'selected' if carrier=='DHL' else ''}>DHL</option>
        <option value="Cargus" {'selected' if carrier=='Cargus' else ''}>Cargus</option>
        <option value="SameDay" {'selected' if carrier=='SameDay' else ''}>SameDay</option>
        <option value="FanCourier" {'selected' if carrier=='FanCourier' else ''}>FanCourier</option>
        <option value="GLS" {'selected' if carrier=='GLS' else ''}>GLS</option>
        </select></div></div>
        <label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:6px">NEW STATUS</label>
        <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">'''
        for st in STATUSES:
            selected = 'border:2px solid #c9a227;background:rgba(201,162,39,.15)' if st['key'] == safe_get(o,'status','new') else ''
            orders_html += f'<label style="display:flex;align-items:center;gap:4px;padding:8px 14px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:6px;font-size:11px;color:{st["color"]};cursor:pointer;{selected}"><input type="radio" name="status" value="{st["key"]}" {"checked" if st["key"]==safe_get(o,"status","new") else ""} style="accent-color:#c9a227">{st["icon"]} {st["label"]}</label>'
        orders_html += f'''</div>
        <div style="display:flex;gap:10px;align-items:center;margin-top:8px">
        <button type="submit" style="padding:12px 28px;background:#c9a227;color:#1a0a0e;border:none;border-radius:6px;font-weight:700;font-size:12px;letter-spacing:1px;cursor:pointer">📧 Update & Send Email</button>
        <span style="font-size:11px;color:#666">Email will be sent to {email}</span>
        </div>
        <div style="margin-top:14px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);border-radius:8px;padding:16px">
        <p style="font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:10px">✏️ EDITABLE EMAIL</p>
        <div style="margin-bottom:12px">
        <label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">EMAIL SUBJECT</label>
        <input name="custom_subject" placeholder="Leave empty for auto subject" style="width:100%;padding:10px;border-radius:6px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#fff;font-size:13px;outline:none">
        </div>
        <div style="margin-bottom:12px">
        <label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">CUSTOM MESSAGE <span style="color:#666;font-weight:400">(optional)</span></label>
        <textarea name="custom_body" id="emailBody_{oid}" rows="4" placeholder="Leave empty to send the branded auto-email with product image, status, and tracking." style="width:100%;padding:12px;border-radius:8px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#e0d6c8;font-family:Helvetica,sans-serif;font-size:13px;resize:vertical;outline:none;line-height:1.6"></textarea>
        </div>
        <p style="margin:8px 0 0;font-size:10px;color:#555">💡 Auto email includes: greeting, status badge, product card with image, tracking info, and branded footer.</p>
        </div>
        </form>
        </details>
        </div>'''

    messages_html = ''
    for m in messages:
        replies = json.loads(m['replies'] or '[]')
        status_color = '#3b82f6' if m['status'] == 'new' else '#22c55e' if m['status'] == 'replied' else '#888'
        status_label = 'New' if m['status'] == 'new' else 'Replied' if m['status'] == 'replied' else m['status']
        replies_html = ''
        for r in replies:
            replies_html += f'''<div style="background:rgba(201,162,39,.05);border-left:3px solid #c9a227;padding:12px;margin:8px 0;border-radius:0 6px 6px 0">
            <p style="margin:0 0 4px;font-size:11px;color:#c9a227;font-weight:700">You replied — {r.get("date","")[:16]}</p>
            <p style="margin:0;font-size:13px;color:#ccc;white-space:pre-wrap">{r.get("text","")}</p></div>'''
        messages_html += f'''<div style="background:#1a0e0e;border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:20px;margin-bottom:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
        <div><span style="color:#c9a227;font-size:16px;font-weight:700">{m['name']}</span>
        <span style="color:#999999 !important;font-size:12px;margin-left:8px">&lt;{m['email']}&gt;</span></div>
        <span style="background:{status_color}18;color:{status_color};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:700">{status_label}</span></div>
        <div style="margin:8px 0;font-size:14px;color:#fff;font-weight:600">{m['subject']}{f' — Order #{m["order_number"]}' if m['order_number'] else ''}</div>
        <div style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:8px;padding:14px;margin:10px 0">
        <p style="margin:0;font-size:13px;color:#ccc;line-height:1.6;white-space:pre-wrap">{m['message']}</p></div>
        <div style="font-size:11px;color:#666;margin-bottom:8px">📅 {m['created_at'][:16] if m['created_at'] else ''}</div>
        {replies_html}
        
        <details style="margin-top:10px">
        <summary style="color:#c9a227;font-size:12px;font-weight:700;cursor:pointer;letter-spacing:1px;padding:8px 0">💬 REPLY TO {m['name'].upper()}</summary>
        <form action="/admin/reply" method="POST" style="margin-top:10px">
        <input type="hidden" name="pw" value="{pw}">
        <input type="hidden" name="msg_id" value="{m['id']}">
        <input type="hidden" name="to_email" value="{m['email']}">
        <input type="hidden" name="to_name" value="{m['name']}">
        <input type="hidden" name="subject" value="Re: {m['subject']}">
        <textarea name="reply_text" id="reply_{m['id']}" placeholder="Type your reply to {m['name']}..." oninput="document.getElementById('preview_{m['id']}').innerText=this.value" style="width:100%;padding:12px;border-radius:8px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#e0d6c8;font-family:Helvetica,sans-serif;font-size:13px;min-height:100px;resize:vertical;outline:none"></textarea>
        
        <div style="margin-top:12px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);border-radius:8px;padding:16px">
        <p style="font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:10px">📧 EMAIL PREVIEW — to {m['email']}</p>
        <div style="background:#1a0a0e;border:1px solid #2a1a1e;border-radius:8px;padding:20px;font-size:13px">
        <div style="text-align:center;padding-bottom:15px;border-bottom:1px solid rgba(201,162,39,.1);margin-bottom:15px">
        <p style="color:#c9a227;font-size:12px;font-weight:700;letter-spacing:2px;margin:0">VEXORA MAISON</p></div>
        <p style="color:#ccc;margin:0 0 10px">Hi {m['name']},</p>
        <p style="color:#ccc;margin:0 0 10px">Thank you for reaching out! Here's our response:</p>
        <div style="background:rgba(201,162,39,.05);border:1px solid #2a1a1e;border-radius:6px;padding:15px;margin:10px 0">
        <p id="preview_{m['id']}" style="color:#e0d6c8;margin:0;font-size:13px;line-height:1.6;white-space:pre-wrap;min-height:30px;color:#aaa;font-style:italic">Your reply will appear here...</p></div>
        <p style="color:#999999 !important;font-size:12px;margin:10px 0 0">For faster response, DM us on Instagram <span style="color:#c9a227">@vexoramaison</span></p>
        <div style="margin-top:15px;padding-top:10px;border-top:1px solid rgba(201,162,39,.1);text-align:center">
        <p style="color:#666666 !important;font-size:10px;margin:0">© Vexora Maison — support@vexoramaison.com</p></div>
        </div></div>

        <button type="submit" style="margin-top:12px;padding:12px 28px;background:#c9a227;color:#1a0a0e;border:none;border-radius:6px;font-weight:700;font-size:12px;letter-spacing:1px;cursor:pointer">📧 Send Reply Email</button>
        <span style="font-size:11px;color:#666;margin-left:10px">from support@vexoramaison.com</span>
        </form></details></div>'''

    html = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Vexora Admin</title>
    <style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#0f0609;color:#e0d6c8;font-family:Helvetica,Arial,sans-serif;min-height:100vh}}
    .topbar{{background:#1a0e0e;padding:16px 24px;border-bottom:1px solid rgba(201,162,39,.2);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}}
    .topbar h1{{color:#c9a227;font-size:16px;letter-spacing:3px}}
    .tabs{{display:flex;gap:4px;background:#1a0e0e;padding:8px 24px;border-bottom:1px solid rgba(255,255,255,.05)}}
    .tab{{padding:10px 20px;color:#888;text-decoration:none;font-size:13px;font-weight:600;border-radius:6px;transition:.2s}}
    .tab:hover{{background:rgba(201,162,39,.08);color:#c9a227}}
    .tab.active{{background:rgba(201,162,39,.1);color:#c9a227}}
    .badge{{background:#ef4444;color:#fff;font-size:10px;font-weight:800;padding:2px 7px;border-radius:10px;margin-left:6px}}
    .content{{max-width:900px;margin:20px auto;padding:0 20px}}
    </style></head><body>
    <div class="topbar"><h1>VEXORA ADMIN</h1><span style="font-size:12px;color:#888">{len(orders)} orders | {len(messages)} messages | {len(subscribers)} subscribers</span></div>
    <div class="tabs">
    <a href="/admin?pw={pw}&tab=orders" class="tab {'active' if tab=='orders' else ''}">📦 Orders ({len(orders)})</a>
    <a href="/admin?pw={pw}&tab=messages" class="tab {'active' if tab=='messages' else ''}">💬 Messages ({len(messages)}){'<span class=badge>'+str(unread)+'</span>' if unread else ''}</a>
    <a href="/admin?pw={pw}&tab=subscribers" class="tab {'active' if tab=='subscribers' else ''}">📧 Subscribers ({len(subscribers)})</a>
    </div>
    <div class="content">'''

    if tab == 'orders':
        html += f'''<details style="margin-bottom:20px">
        <summary style="background:linear-gradient(135deg,rgba(201,162,39,.12),rgba(201,162,39,.05));border:1px solid rgba(201,162,39,.25);border-radius:10px;padding:14px 20px;cursor:pointer;color:#c9a227;font-size:13px;font-weight:700;letter-spacing:1px;list-style:none;display:flex;align-items:center;gap:8px">
        <span style="font-size:18px">➕</span> ADAUGĂ COMANDĂ MANUALĂ</summary>
        <form action="/admin/add-order" method="POST" style="background:#1a0e0e;border:1px solid #2a1a1e;border-radius:0 0 10px 10px;padding:20px;margin-top:-4px">
        <input type="hidden" name="pw" value="{pw}">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div><label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">CUSTOMER NAME *</label>
        <input name="shipping_name" required placeholder="e.g. Ion Popescu" style="width:100%;padding:10px;border-radius:6px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#fff;font-size:13px;outline:none"></div>
        <div><label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">EMAIL *</label>
        <input name="customer_email" type="email" required placeholder="client@email.com" style="width:100%;padding:10px;border-radius:6px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#fff;font-size:13px;outline:none"></div>
        <div><label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">PHONE</label>
        <input name="shipping_phone" placeholder="07xx xxx xxx" style="width:100%;padding:10px;border-radius:6px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#fff;font-size:13px;outline:none"></div>
        <div><label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">PRODUCT NAME *</label>
        <div style="position:relative">
        <input id="manualProductSearch" name="product_name" autocomplete="off" required placeholder="🔍 Search product..." oninput="searchProducts(this.value)" style="width:100%;padding:10px;border-radius:6px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#fff;font-size:13px;outline:none">
        <input type="hidden" name="product_image" id="manualProductImage">
        <div id="manualProductResults" style="display:none;position:absolute;top:calc(100% + 4px);left:0;right:0;background:#1a0a0e;border:1px solid rgba(201,162,39,.2);border-radius:8px;max-height:280px;overflow-y:auto;z-index:100;box-shadow:0 12px 30px rgba(0,0,0,.6)"></div>
        </div>
        <div id="manualProductPreview" style="display:none;margin-top:10px;background:rgba(201,162,39,.05);border:1px solid #2a1a1e;border-radius:8px;padding:12px;display:none">
        </div>
        </div>
        <div><label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">ADDRESS</label>
        <input name="shipping_address" placeholder="Str. Exemplu Nr. 1" style="width:100%;padding:10px;border-radius:6px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#fff;font-size:13px;outline:none"></div>
        <div><label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">CITY</label>
        <input name="shipping_city" placeholder="București" style="width:100%;padding:10px;border-radius:6px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#fff;font-size:13px;outline:none"></div>
        <div><label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">TOTAL PRICE</label>
        <input name="total" placeholder="425.00" style="width:100%;padding:10px;border-radius:6px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#fff;font-size:13px;outline:none"></div>
        <div><label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">CURRENCY</label>
        <select name="currency" style="width:100%;padding:10px;border-radius:6px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#fff;font-size:13px;outline:none">
        <option value="RON">RON</option><option value="EUR">EUR</option></select></div>
        </div>
        <div style="margin-top:12px"><label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">VENDOR URL (optional)</label>
        <input name="product_url" placeholder="https://kakobuy.com/..." style="width:100%;padding:10px;border-radius:6px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#fff;font-size:13px;outline:none"></div>
        <button type="submit" style="margin-top:16px;padding:14px 32px;background:#c9a227;color:#1a0a0e;border:none;border-radius:8px;font-weight:700;font-size:13px;letter-spacing:1px;cursor:pointer;width:100%">➕ ADAUGĂ COMANDA</button>
        </form>
        </details>'''
        # Add product search script OUTSIDE of f-string to avoid escaping issues
        import html as html_lib
        safe_products = html_lib.escape(shopify_products_json)
        html += f'<div id="vxProductsData" style="display:none" data-products="{safe_products}"></div>'
        html += '''<script>
        var _allProducts=[];
        try{var d=document.getElementById('vxProductsData');if(d)_allProducts=JSON.parse(d.getAttribute('data-products'))}catch(e){console.log('Products parse:',e)}
        function searchProducts(q){
          var res=document.getElementById('manualProductResults');
          document.getElementById('manualProductSearch').value=q;
          if(q.length<2){res.style.display='none';return}
          var ql=q.toLowerCase();
          var matches=_allProducts.filter(function(p){return p.t.toLowerCase().indexOf(ql)!==-1}).slice(0,6);
          if(!matches.length){
            res.innerHTML='<div style="padding:14px;color:#666;font-size:12px;text-align:center">No products found</div>';
            res.style.display='block';return;
          }
          var h='';
          matches.forEach(function(p){
            h+='<div style="display:flex;align-items:center;gap:12px;padding:10px 14px;cursor:pointer;border-bottom:1px solid rgba(255,255,255,.03)" onmouseover="this.style.background=\\'rgba(201,162,39,.08)\\'" onmouseout="this.style.background=\\'transparent\\'" onclick="pickProd(this)"'
            +' data-t="'+p.t.replace(/"/g,'&quot;')+'" data-i="'+(p.i||'')+'" data-p="'+(p.p||'')+'">'
            +(p.i?'<img src="'+p.i+'" style="width:48px;height:48px;object-fit:cover;border-radius:6px;border:1px solid rgba(201,162,39,.1)" onerror="this.style.display=\\'none\\'">':'<div style="width:48px;height:48px;background:#2a1015;border-radius:6px;display:flex;align-items:center;justify-content:center;color:#555;font-size:18px">📦</div>')
            +'<div style="flex:1;min-width:0"><div style="font-size:13px;font-weight:600;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+p.t+'</div>'
            +'<div style="font-size:12px;color:#c9a227;font-weight:700;margin-top:2px">'+(p.p?p.p+' lei':'')+'</div></div></div>';
          });
          res.innerHTML=h;res.style.display='block';
        }
        function pickProd(el){
          var t=el.getAttribute('data-t'),i=el.getAttribute('data-i'),p=el.getAttribute('data-p');
          document.getElementById('manualProductSearch').value=t;
          document.getElementById('manualProductImage').value=i;
          document.getElementById('manualProductSearch').value=t;
          document.getElementById('manualProductResults').style.display='none';
          var pv=document.getElementById('manualProductPreview');
          pv.innerHTML='<div style="display:flex;align-items:center;gap:12px">'
            +(i?'<img src="'+i.replace('width=100','width=120')+'" style="width:60px;height:60px;object-fit:cover;border-radius:8px;border:1px solid rgba(201,162,39,.2)">':'')
            +'<div><div style="font-size:14px;font-weight:700;color:#fff">'+t+'</div>'
            +(p?'<div style="font-size:13px;color:#c9a227;font-weight:700;margin-top:3px">'+p+' lei</div>':'')+'</div>'
            +'<span onclick="clrProd()" style="margin-left:auto;cursor:pointer;color:#666;font-size:16px">&#x2715;</span></div>';
          pv.style.display='block';
          if(p){var ti=document.querySelector('input[name=total]');if(ti&&!ti.value)ti.value=p}
        }
        function clrProd(){
          document.getElementById('manualProductSearch').value='';
          document.getElementById('manualProductImage').value='';
          document.getElementById('manualProductSearch').value='';
          document.getElementById('manualProductPreview').style.display='none';
        }
        document.addEventListener('click',function(e){
          if(!e.target.closest('#manualProductResults')&&!e.target.closest('#manualProductSearch'))
            document.getElementById('manualProductResults').style.display='none';
        });
        </script>'''
        html += '<div>' + orders_html + '</div>' if orders_html else '<p style="text-align:center;color:#555;padding:40px">No orders yet.</p>'
    elif tab == 'messages':
        # Success message for sent direct email from messages tab
        direct_sent = request.args.get('direct_sent', '')
        if direct_sent:
            html += f'<div style="background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.25);border-radius:8px;padding:14px;margin-bottom:16px;text-align:center"><p style="margin:0;color:#22c55e;font-size:14px;font-weight:700">✅ Email sent to {direct_sent} recipient(s)!</p></div>'
        
        # Compose New Email form with rich text + live preview
        html += f'''<div style="background:#1a0e0e;border:1px solid rgba(201,162,39,.2);border-radius:10px;padding:20px;margin-bottom:20px">
        <details open>
        <summary style="color:#c9a227;font-size:14px;font-weight:700;cursor:pointer;letter-spacing:2px;padding:4px 0">📨 COMPOSE NEW EMAIL</summary>
        <form action="/admin/send-message" method="POST" id="composeForm" style="margin-top:16px">
        <input type="hidden" name="pw" value="{pw}">
        <input type="hidden" name="msg_body_html" id="msgBodyHtml">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">
        <div>
        <label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">TO (email)</label>
        <input name="msg_to" id="cmpTo" placeholder="email@example.com" oninput="updateComposePreview()" style="width:100%;padding:12px;border-radius:8px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#e0d6c8;font-size:13px;outline:none;box-sizing:border-box">
        </div>
        <div>
        <label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">RECIPIENT NAME <span style="color:#666;font-weight:400">(optional)</span></label>
        <input name="msg_name" id="cmpName" placeholder="e.g. John" oninput="updateComposePreview()" style="width:100%;padding:12px;border-radius:8px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#e0d6c8;font-size:13px;outline:none;box-sizing:border-box">
        </div>
        </div>
        <div style="margin-bottom:12px">
        <label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">SUBJECT</label>
        <input name="msg_subject" id="cmpSubject" placeholder="e.g. Your order update" oninput="updateComposePreview()" style="width:100%;padding:12px;border-radius:8px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#e0d6c8;font-size:13px;outline:none;box-sizing:border-box">
        </div>
        <div style="margin-bottom:4px">
        <label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">MESSAGE</label>
        </div>
        <div style="display:flex;gap:2px;padding:8px 10px;background:rgba(201,162,39,.06);border:1px solid #2a1a1e;border-bottom:none;border-radius:8px 8px 0 0;flex-wrap:wrap">
        <button type="button" onclick="fmtCmd('bold')" title="Bold" style="background:transparent;border:none;color:#999;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:13px;font-weight:900;font-family:serif">B</button>
        <button type="button" onclick="fmtCmd('italic')" title="Italic" style="background:transparent;border:none;color:#999;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:13px;font-style:italic;font-family:serif"><i>I</i></button>
        <button type="button" onclick="fmtCmd('underline')" title="Underline" style="background:transparent;border:none;color:#999;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:13px;text-decoration:underline;font-family:serif"><u>U</u></button>
        <span style="width:1px;background:rgba(201,162,39,.2);margin:0 6px"></span>
        <button type="button" onclick="fmtCmd('insertUnorderedList')" title="Bullet list" style="background:transparent;border:none;color:#999;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:12px">• List</button>
        <button type="button" onclick="fmtCmd('insertOrderedList')" title="Numbered list" style="background:transparent;border:none;color:#999;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:12px">1. List</button>
        <span style="width:1px;background:rgba(201,162,39,.2);margin:0 6px"></span>
        <button type="button" onclick="fmtCmd('formatBlock','<h2>')" title="Heading" style="background:transparent;border:none;color:#999;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:13px;font-weight:800">H</button>
        <button type="button" onclick="fmtCmd('formatBlock','<p>')" title="Paragraph" style="background:transparent;border:none;color:#999;padding:5px 10px;border-radius:4px;cursor:pointer;font-size:11px">¶</button>
        <span style="width:1px;background:rgba(201,162,39,.2);margin:0 6px"></span>
        <select onchange="if(this.value){{document.execCommand('foreColor',false,this.value)}};this.value=''" style="background:#0f0609;border:1px solid rgba(201,162,39,.2);color:#999;padding:4px 8px;border-radius:4px;font-size:10px;cursor:pointer;outline:none">
        <option value="">Color</option>
        <option value="#c9a227" style="color:#c9a227">Gold</option>
        <option value="#ffffff" style="color:#fff">White</option>
        <option value="#22c55e" style="color:#22c55e">Green</option>
        <option value="#ef4444" style="color:#ef4444">Red</option>
        <option value="#999999" style="color:#999">Gray</option>
        </select>
        </div>
        <div contenteditable="true" id="cmpEditor" oninput="updateComposePreview()" data-placeholder="Write your email message..." style="min-height:140px;padding:14px 16px;border-radius:0 0 8px 8px;border:1px solid #2a1a1e;border-top:none;background:#0f0609;color:#e0d6c8;font-family:Helvetica,sans-serif;font-size:13px;line-height:1.7;outline:none;overflow-y:auto;max-height:300px"></div>
        <style>#cmpEditor:empty:before{{content:attr(data-placeholder);color:#555;pointer-events:none}}</style>

        <div style="margin-top:16px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);border-radius:10px;padding:18px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px">
        <p style="font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin:0">📧 LIVE EMAIL PREVIEW</p>
        <span id="cmpPreviewTo" style="font-size:10px;color:#666">to: —</span>
        </div>
        <div style="background:#080305;border:1px solid rgba(201,162,39,.12);border-radius:12px;overflow:hidden;max-width:420px;margin:0 auto">
        <div style="background:linear-gradient(180deg,#1a0f14,#120810);padding:22px 16px 16px;text-align:center;border-bottom:1px solid rgba(201,162,39,.12)">
        <img src="https://cdn.shopify.com/s/files/1/1013/0466/4412/files/cropped_circle_image.png?v=1774793294" alt="V" width="40" height="40" style="border-radius:50%;border:2px solid rgba(201,162,39,.4);display:inline-block;margin:0 auto 8px">
        <p style="margin:0;color:#c9a227;font-size:10px;font-weight:700;letter-spacing:4px;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;letter-spacing:5px">VEXORA MAISON</p>
        </div>
        <div style="padding:22px 18px 16px;background:#0f0609">
        <p id="cmpPreviewSubject" style="margin:0 0 6px;font-size:18px;color:#fff;text-align:center;font-weight:800;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif">Subject line</p>
        <div style="width:30px;height:2px;background:linear-gradient(90deg,transparent,#c9a227,transparent);margin:0 auto 18px"></div>
        <div id="cmpPreviewName" style="margin:0 0 12px;font-size:13px;color:#aaa">Hi there,</div>
        <div id="cmpPreviewBody" style="font-size:13px;color:#ccc;line-height:1.7;min-height:40px">
        <span style="color:#555;font-style:italic">Your message preview...</span></div>
        <div style="text-align:center;margin-top:20px">
        <span style="display:inline-block;padding:12px 32px;background:linear-gradient(135deg,#d4a82a,#b89220);color:#0f0609;border-radius:8px;font-size:10px;font-weight:800;letter-spacing:2px;box-shadow:0 4px 12px rgba(201,162,39,.25)">VISIT OUR STORE</span>
        </div>
        </div>
        <div style="padding:14px 16px 10px;background:#0f0609;text-align:center;border-top:1px solid rgba(201,162,39,.05)">
        <div style="display:inline-block;background:rgba(201,162,39,.08);border:1px solid #2a1a1e;border-radius:20px;padding:3px 14px;margin-bottom:8px">
        <span style="color:#c9a227;font-size:7px;font-weight:800;letter-spacing:3px">FOLLOW US</span>
        </div><br>
        <span style="color:#999;font-size:8px;letter-spacing:1px">&#x1F4F8; INSTAGRAM &nbsp;|&nbsp; &#x1F3B5; TIKTOK &nbsp;|&nbsp; &#x1F4AC; WHATSAPP</span>
        </div>
        <div style="background:#070204;padding:10px 16px;text-align:center">
        <p style="margin:0;color:#555;font-size:7px;letter-spacing:.5px">&copy; 2022 Vexora Maison &mdash; All rights reserved</p>
        </div>
        </div>
        </div>

        <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:16px">
        <button type="submit" onclick="document.getElementById('msgBodyHtml').value=document.getElementById('cmpEditor').innerHTML" style="padding:14px 30px;background:#c9a227;color:#1a0a0e;border:none;border-radius:6px;font-weight:700;font-size:12px;letter-spacing:1px;cursor:pointer">📧 Send Email</button>
        <span style="font-size:11px;color:#666">Sent from orders@vexoramaison.com with Vexora branded template</span>
        </div>
        </form>
        </details>
        </div>

        <script>
        function fmtCmd(cmd,val){{document.execCommand(cmd,false,val||null);document.getElementById('cmpEditor').focus();updateComposePreview()}}
        function updateComposePreview(){{
          var to=document.getElementById('cmpTo').value||'—';
          var name=document.getElementById('cmpName').value||'there';
          var subj=document.getElementById('cmpSubject').value||'Subject line';
          var body=document.getElementById('cmpEditor').innerHTML;
          document.getElementById('cmpPreviewTo').textContent='to: '+to;
          document.getElementById('cmpPreviewSubject').textContent=subj;
          document.getElementById('cmpPreviewName').innerHTML='Hi <strong style="color:#fff">'+name+'</strong>,';
          var preview=body.replace(/<div><br><\\/div>/g,'').trim();
          document.getElementById('cmpPreviewBody').innerHTML=preview||'<span style="color:#555;font-style:italic">Your message preview...</span>';
        }}
        </script>'''
        
        html += '<div>' + messages_html + '</div>' if messages_html else '<p style="text-align:center;color:#555;padding:40px">No messages yet.</p>'
    elif tab == 'subscribers':
        sent_count = request.args.get('sent', '')
        if sent_count:
            html += f'<div style="background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.25);border-radius:8px;padding:14px;margin-bottom:16px;text-align:center"><p style="margin:0;color:#22c55e;font-size:14px;font-weight:700">✅ Newsletter sent to {sent_count} subscribers!</p></div>'
        
        added_count = request.args.get('added', '')
        if added_count:
            html += f'<div style="background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.25);border-radius:8px;padding:14px;margin-bottom:16px;text-align:center"><p style="margin:0;color:#22c55e;font-size:14px;font-weight:700">✅ {added_count} email(s) added to subscriber list!</p></div>'
        
        # Newsletter log
        db2 = get_db()
        db2.execute('''CREATE TABLE IF NOT EXISTS newsletter_log(id INTEGER PRIMARY KEY AUTOINCREMENT, template_id TEXT, subject TEXT, sent_at TEXT, recipients INTEGER, status TEXT)''')
        nl_log = db2.execute("SELECT * FROM newsletter_log ORDER BY sent_at DESC LIMIT 10").fetchall()
        last_sent = nl_log[0] if nl_log else None
        days_since = 0
        if last_sent and last_sent['sent_at']:
            days_since = (datetime.datetime.now() - datetime.datetime.fromisoformat(last_sent['sent_at'])).days
        db2.close()

        # Auto-send status
        auto_status = f'<span style="color:#22c55e">✅ Sent {days_since} days ago</span>' if last_sent else '<span style="color:#f59e0b">⚠️ Never sent</span>'
        if days_since >= AUTO_NEWSLETTER_DAYS:
            auto_status = f'<span style="color:#ef4444">🔴 Due! Last sent {days_since} days ago</span>'

        html += f'''<div style="background:#1a0e0e;border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:20px;margin-bottom:16px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px">
        <h3 style="color:#c9a227;font-size:16px;font-weight:700;letter-spacing:2px;margin:0">📧 NEWSLETTER MANAGEMENT</h3>
        <span style="font-size:12px">{auto_status} · Auto every {AUTO_NEWSLETTER_DAYS} days</span></div>

        <details style="margin-bottom:16px">
        <summary style="color:#c9a227;font-size:12px;font-weight:700;cursor:pointer;padding:8px 0;letter-spacing:1px">📝 SEND CUSTOM NEWSLETTER</summary>
        <form action="/admin/newsletter" method="POST" style="margin-top:12px">
        <input type="hidden" name="pw" value="{pw}">
        <input type="hidden" name="action" value="custom">
        <div style="margin-bottom:12px">
        <label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">SUBJECT LINE</label>
        <input name="nl_subject" placeholder="e.g. 🔥 New Drops Just Landed!" style="width:100%;padding:12px;border-radius:8px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#e0d6c8;font-size:13px;outline:none">
        </div>
        <div style="margin-bottom:12px">
        <label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">MESSAGE BODY</label>
        <textarea name="nl_body" id="nlBody" rows="6" placeholder="Write your newsletter message..." oninput="document.getElementById('nlPreviewText').innerText=this.value" style="width:100%;padding:12px;border-radius:8px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#e0d6c8;font-family:Helvetica,sans-serif;font-size:13px;resize:vertical;outline:none"></textarea>
        </div>
        <div style="background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);border-radius:8px;padding:16px;margin-bottom:12px">
        <p style="font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:10px">📧 EMAIL PREVIEW</p>
        <div style="background:#1a0a0e;border:1px solid #2a1a1e;border-radius:8px;padding:20px;font-size:13px">
        <div style="text-align:center;padding-bottom:12px;border-bottom:1px solid rgba(201,162,39,.1);margin-bottom:12px"><p style="color:#c9a227;font-size:12px;font-weight:700;letter-spacing:2px;margin:0">VEXORA MAISON</p></div>
        <p id="nlPreviewText" style="color:#ccc;margin:0;min-height:40px;white-space:pre-wrap;font-style:italic;line-height:1.6">Your message preview...</p>
        <div style="text-align:center;margin-top:15px"><span style="display:inline-block;padding:10px 24px;background:#c9a227;color:#1a0a0e;border-radius:6px;font-size:11px;font-weight:700;letter-spacing:1px">SHOP NOW</span></div>
        <div style="margin-top:12px;padding-top:8px;border-top:1px solid rgba(201,162,39,.1);text-align:center"><p style="color:#555;font-size:9px;margin:0">© Vexora Maison · support@vexoramaison.com · Dezabonare</p></div>
        </div></div>
        <button type="submit" style="padding:12px 28px;background:#c9a227;color:#1a0a0e;border:none;border-radius:6px;font-weight:700;font-size:12px;letter-spacing:1px;cursor:pointer">📧 Send to All {len(subscribers)} Subscribers</button>
        <span style="font-size:11px;color:#666;margin-left:10px">from support@vexoramaison.com</span>
        </form></details>

        <details style="margin-bottom:16px">
        <summary style="color:#c9a227;font-size:12px;font-weight:700;cursor:pointer;padding:8px 0;letter-spacing:1px">🎨 SEND PRE-MADE TEMPLATE</summary>
        <div style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:10px">'''

        for tpl in NEWSLETTER_TEMPLATES:
            html += f'''<form action="/admin/newsletter" method="POST" style="margin:0">
            <input type="hidden" name="pw" value="{pw}">
            <input type="hidden" name="action" value="template">
            <input type="hidden" name="template_id" value="{tpl['id']}">
            <button type="submit" style="width:100%;padding:16px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:8px;color:#fff;cursor:pointer;text-align:left;transition:border-color .2s;font-family:Helvetica,sans-serif" onmouseover="this.style.borderColor='rgba(201,162,39,.3)'" onmouseout="this.style.borderColor='rgba(255,255,255,.08)'">
            <p style="margin:0 0 4px;font-size:13px;font-weight:700;color:#e0d6c8">{tpl['subject']['ro']}</p>
            <p style="margin:0;font-size:10px;color:#888;letter-spacing:1px;text-transform:uppercase">{tpl['id'].replace('_',' ')}</p>
            </button></form>'''

        html += f'''</div></details>

        <details style="margin-bottom:16px">
        <summary style="color:#c9a227;font-size:12px;font-weight:700;cursor:pointer;padding:8px 0;letter-spacing:1px">🤖 AUTO-SEND (every {AUTO_NEWSLETTER_DAYS} days)</summary>
        <div style="margin-top:12px;background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);border-radius:8px;padding:16px">
        <p style="color:#ccc;font-size:13px;margin:0 0 10px">Auto-newsletters pick a random template and send to all active subscribers every {AUTO_NEWSLETTER_DAYS} days.</p>
        <p style="color:#999999 !important;font-size:12px;margin:0 0 10px">Cron URL (add to <a href="https://cron-job.org" target="_blank" style="color:#c9a227">cron-job.org</a> — free, runs daily):</p>
        <input readonly onclick="this.select()" value="{RAILWAY_URL}/cron/newsletter" style="width:100%;padding:10px;background:#0f0609;border:1px solid rgba(201,162,39,.2);border-radius:6px;color:#c9a227;font-size:12px;outline:none;font-family:monospace">
        <p style="color:#666;font-size:11px;margin:8px 0 0">Set cron to run once daily. It auto-skips if last newsletter was sent less than {AUTO_NEWSLETTER_DAYS} days ago.</p>
        </div></details>

        <details>
        <summary style="color:#c9a227;font-size:12px;font-weight:700;cursor:pointer;padding:8px 0;letter-spacing:1px">📋 SEND HISTORY ({len(nl_log)} recent)</summary>
        <div style="margin-top:12px">'''
        
        if nl_log:
            for nl in nl_log:
                html += f'<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.04)"><div><span style="color:#fff;font-size:13px">{nl["subject"] or nl["template_id"]}</span></div><div style="text-align:right"><span style="color:#c9a227;font-size:12px;font-weight:600">{nl["recipients"]} sent</span><br><span style="color:#666;font-size:11px">{nl["sent_at"][:16] if nl["sent_at"] else ""}</span></div></div>'
        else:
            html += '<p style="color:#555;font-size:12px;text-align:center;padding:15px 0">No newsletters sent yet.</p>'
        
        html += '</div></details></div>'

        # ===== ADD EMAILS MANUALLY + SEND DIRECT EMAIL =====
        html += f'''<div style="background:#1a0e0e;border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:20px;margin-bottom:16px">
        <h3 style="color:#c9a227;font-size:14px;font-weight:700;letter-spacing:2px;margin:0 0 16px">✉️ DIRECT EMAIL & ADD SUBSCRIBERS</h3>
        
        <details style="margin-bottom:16px">
        <summary style="color:#c9a227;font-size:12px;font-weight:700;cursor:pointer;padding:8px 0;letter-spacing:1px">➕ ADD EMAILS TO SUBSCRIBER LIST</summary>
        <form action="/admin/add-subscriber" method="POST" style="margin-top:12px">
        <input type="hidden" name="pw" value="{pw}">
        <div style="margin-bottom:12px">
        <label style="display:block;font-size:10px;color:#c9a227;font-weight:700;letter-spacing:1px;margin-bottom:4px">EMAIL ADDRESSES <span style="color:#666;font-weight:400">(one per line or comma separated)</span></label>
        <textarea name="emails" rows="4" placeholder="email1@example.com&#10;email2@example.com&#10;email3@example.com" style="width:100%;padding:12px;border-radius:8px;border:1px solid rgba(201,162,39,.2);background:#0f0609;color:#e0d6c8;font-family:monospace;font-size:13px;resize:vertical;outline:none"></textarea>
        </div>
        <div style="display:flex;gap:10px;align-items:center">
        <button type="submit" style="padding:12px 24px;background:#c9a227;color:#1a0a0e;border:none;border-radius:6px;font-weight:700;font-size:12px;letter-spacing:1px;cursor:pointer">➕ Add to Subscribers</button>
        <span style="font-size:11px;color:#666">They will receive future newsletters automatically</span>
        </div>
        </form></details>
        </div>'''

        # Subscriber list
        if subscribers:
            html += '<div style="background:#1a0e0e;border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:20px;margin-bottom:16px">'
            html += f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px"><h3 style="color:#c9a227;font-size:14px;font-weight:700;letter-spacing:2px;margin:0">SUBSCRIBERS</h3><span style="color:#999999 !important;font-size:12px">{len(subscribers)} total</span></div>'
            html += '<div style="background:rgba(201,162,39,.05);border:1px solid rgba(201,162,39,.1);border-radius:8px;padding:12px;margin-bottom:16px"><p style="margin:0;color:#999999 !important;font-size:12px">📋 All emails: <input readonly onclick="this.select()" value="' + ', '.join([s['email'] for s in subscribers]) + '" style="width:100%;margin-top:8px;padding:10px;background:#0f0609;border:1px solid rgba(201,162,39,.2);border-radius:6px;color:#e0d6c8;font-size:12px;outline:none"></p></div>'
            for s in subscribers:
                html += f'<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.04)"><span style="color:#fff;font-size:13px">{s["email"]}</span><span style="color:#666;font-size:11px">{s["subscribed_at"][:16] if s["subscribed_at"] else ""}</span></div>'
            html += '</div>'
        else:
            html += '<p style="text-align:center;color:#555;padding:20px">No subscribers yet.</p>'

    html += '</div></body></html>'

    resp = make_response(html)
    resp.set_cookie('dpw', pw, max_age=86400*30)
    return resp

# ===================== ADMIN REPLY =====================
@app.route('/admin/reply', methods=['POST'])
def admin_reply():
    pw = request.form.get('pw', '')
    if pw != DASH_PASS:
        return redirect('/admin')
    msg_id = request.form.get('msg_id')
    to_email = request.form.get('to_email')
    to_name = request.form.get('to_name')
    subject = request.form.get('subject')
    reply_text = request.form.get('reply_text', '').strip()
    if not reply_text:
        return redirect(f'/admin?pw={pw}&tab=messages')
    
    # Save reply to DB
    now = datetime.datetime.now().isoformat()
    db = get_db()
    row = db.execute('SELECT replies FROM messages WHERE id=?', (msg_id,)).fetchone()
    replies = json.loads(row['replies'] or '[]') if row else []
    replies.append({'text': reply_text, 'date': now})
    db.execute('UPDATE messages SET replies=?, status=? WHERE id=?', (json.dumps(replies), 'replied', msg_id))
    db.commit()
    db.close()

    # Send reply email
    body_html = f'''<p style="color:#bbbbbb !important;font-size:15px;line-height:1.7;margin:0 0 24px">Hi <strong style="color:#fff">{to_name}</strong>,</p>
    <p style="color:#999999 !important;font-size:14px;line-height:1.6;margin:0 0 28px">Thank you for reaching out! Here's our response:</p>
    <table cellpadding="0" cellspacing="0" width="100%" style="background-color:#1a1014 !important;border:1px solid #2a1a1e;border-left:3px solid #c9a227;border-radius:0 12px 12px 0;margin:0 0 28px">
    <tr><td style="padding:20px 22px">
    <p style="margin:0;color:#e0d6c8;font-size:14px;line-height:1.75;white-space:pre-wrap">{reply_text}</p>
    </td></tr></table>
    <table cellpadding="0" cellspacing="0" width="100%" style="background-color:#150b0f !important;border:1px solid #221519;border-radius:10px;margin:0">
    <tr><td style="padding:16px 20px">
    <p style="margin:0 0 6px;color:#999999 !important;font-size:13px;line-height:1.6">Need more help? We're here for you:</p>
    <table cellpadding="0" cellspacing="0"><tr>
    <td style="padding-right:20px"><a href="https://instagram.com/vexoramaison" style="color:#c9a227;font-size:12px;text-decoration:none;font-weight:700">Instagram DM</a></td>
    <td style="padding-right:20px"><a href="https://wa.me/40748460032" style="color:#c9a227;font-size:12px;text-decoration:none;font-weight:700">WhatsApp</a></td>
    <td><a href="mailto:support@vexoramaison.com" style="color:#c9a227;font-size:12px;text-decoration:none;font-weight:700">Email</a></td>
    </tr></table>
    </td></tr></table>'''
    send_email(to_email, subject, email_template('VEXORA MAISON', 'Our Response', body_html, 'VISIT OUR STORE', SITE_URL))
    print(f'Reply sent to {to_email}')
    return redirect(f'/admin?pw={pw}&tab=messages')

# ===================== ADMIN SEND NEW MESSAGE (compose) =====================
@app.route('/admin/send-message', methods=['POST'])
def admin_send_message():
    pw = request.form.get('pw', '')
    if pw != DASH_PASS:
        return redirect('/admin')
    
    to_email = request.form.get('msg_to', '').strip()
    name = request.form.get('msg_name', '').strip() or 'there'
    subject = request.form.get('msg_subject', '').strip()
    body_html_raw = request.form.get('msg_body_html', '').strip()
    body_text = request.form.get('msg_body', '').strip()
    
    # Prefer HTML from rich editor, fall back to plain text
    if body_html_raw:
        body_content = body_html_raw
    elif body_text:
        body_content = f'<p style="color:#ccc;font-size:15px;line-height:1.7;white-space:pre-wrap">{body_text}</p>'
    else:
        body_content = ''
    
    if not to_email or not subject or not body_content:
        return redirect(f'/admin?pw={pw}&tab=messages')
    
    # Build email body
    body_html = f'''<p style="color:#bbbbbb !important;font-size:15px;line-height:1.7;margin:0 0 24px">Hi <strong style="color:#fff">{name}</strong>,</p>
    <table cellpadding="0" cellspacing="0" width="100%" style="background-color:#1a1014 !important;border:1px solid #2a1a1e;border-radius:12px;margin:0 0 28px">
    <tr><td style="padding:20px 22px;color:#e0d6c8;font-size:14px;line-height:1.75">
    {body_content}
    </td></tr></table>
    <table cellpadding="0" cellspacing="0" width="100%" style="background-color:#150b0f !important;border:1px solid #221519;border-radius:10px;margin:0">
    <tr><td style="padding:16px 20px">
    <p style="margin:0 0 6px;color:#999999 !important;font-size:13px;line-height:1.6">Need help? We're here for you:</p>
    <table cellpadding="0" cellspacing="0"><tr>
    <td style="padding-right:20px"><a href="https://instagram.com/vexoramaison" style="color:#c9a227;font-size:12px;text-decoration:none;font-weight:700">Instagram DM</a></td>
    <td style="padding-right:20px"><a href="https://wa.me/40748460032" style="color:#c9a227;font-size:12px;text-decoration:none;font-weight:700">WhatsApp</a></td>
    <td><a href="mailto:support@vexoramaison.com" style="color:#c9a227;font-size:12px;text-decoration:none;font-weight:700">Email</a></td>
    </tr></table>
    </td></tr></table>'''
    
    sent = 0
    if send_email(to_email, subject, email_template('VEXORA MAISON', subject, body_html, 'VISIT OUR STORE', SITE_URL)):
        sent = 1
    
    # Save as a message record so it shows in the Messages tab
    import re as _re
    plain_text = _re.sub('<[^<]+?>', '', body_content).strip()[:500] or body_content[:500]
    now = datetime.datetime.now().isoformat()
    db = get_db()
    replies_data = json.dumps([{'text': plain_text, 'date': now}])
    db.execute('INSERT INTO messages(name,email,subject,order_number,message,status,created_at,replies) VALUES(?,?,?,?,?,?,?,?)',
               (name, to_email, subject, '', f'[Outbound email sent by admin]', 'replied', now, replies_data))
    db.commit()
    db.close()
    
    print(f'Direct message sent to {to_email}: {subject}')
    return redirect(f'/admin?pw={pw}&tab=messages&direct_sent={sent}')

# ===================== ADMIN UPDATE ORDER STATUS =====================
@app.route('/admin/update', methods=['GET', 'POST'])
def admin_update():
    pw = request.form.get('pw', request.args.get('pw', ''))
    if pw != DASH_PASS:
        return redirect('/admin')
    oid = request.form.get('id', request.args.get('id'))
    new_status = request.form.get('status', request.args.get('status'))
    tracking = request.form.get('tracking', request.args.get('tracking', ''))
    carrier = request.form.get('carrier', request.args.get('carrier', ''))
    custom_subject = request.form.get('custom_subject', '')
    custom_body = request.form.get('custom_body', '')
    
    s = next((x for x in STATUSES if x['key'] == new_status), None)
    if not s:
        return redirect(f'/admin?pw={pw}')
    
    now = datetime.datetime.now().isoformat()
    db = get_db()
    row = db.execute('SELECT * FROM orders WHERE id=?', (oid,)).fetchone()
    if not row:
        db.close()
        return redirect(f'/admin?pw={pw}')
    
    timeline = json.loads(safe_get(row,'timeline','[]'))
    timeline.append({'status': s['label'], 'date': now, 'icon': s['icon'], 'color': s['color'], 'note': ''})
    
    updates = {'status': new_status, 'updated_at': now, 'timeline': json.dumps(timeline)}
    if tracking:
        updates['tracking_number'] = tracking
        updates['tracking_carrier'] = carrier or 'DHL'
        if 'dhl' in carrier.lower():
            updates['tracking_url'] = f'https://www.dhl.com/en/express/tracking.html?AWB={tracking}'
        elif 'cargus' in carrier.lower():
            updates['tracking_url'] = f'https://www.cargus.ro/tracking/?t={tracking}'
        else:
            updates['tracking_url'] = f'https://parcelsapp.com/en/tracking/{tracking}'
    
    set_clause = ', '.join(f'{k}=?' for k in updates.keys())
    db.execute(f'UPDATE orders SET {set_clause} WHERE id=?', list(updates.values()) + [oid])
    db.commit()
    
    # Send email notification
    email = safe_get(row,'customer_email')
    if email:
        tracking_btn = ''
        tracking_btn_text = ''
        tracking_btn_url = ''
        if tracking and updates.get('tracking_url'):
            tracking_btn_text = f'TRACK WITH {carrier.upper() or "CARRIER"}'
            tracking_btn_url = updates['tracking_url']
        
        # Build product card (always shown in email)
        prod_name = safe_get(row, 'product_name', '')
        prod_img = safe_get(row, 'product_image', '')
        prod_total = safe_get(row, 'total', '')
        prod_currency = safe_get(row, 'currency', 'RON')
        
        # Fallback: if no image stored, try to fetch from WooCommerce
        if prod_name and not prod_img:
            try:
                if WC_KEY and WC_SECRET:
                    r2 = requests.get(f'{WC_URL}/wp-json/wc/v3/products', params={
                        'consumer_key': WC_KEY, 'consumer_secret': WC_SECRET,
                        'search': prod_name.split(' - ')[0].split(' – ')[0].strip()[:50],
                        'per_page': 5
                    }, timeout=10)
                    if r2.status_code == 200:
                        for p in r2.json():
                            if p.get('images') and len(p['images']) > 0:
                                prod_img = p['images'][0].get('src', '')
                                break
            except:
                pass

        product_block = ''
        if prod_name:
            img_cell = ''
            if prod_img:
                img_cell = f'<td style="width:90px;vertical-align:top;padding-right:16px"><a href="{SITE_URL}" style="text-decoration:none"><img src="{prod_img}" alt="{prod_name}" width="90" height="90" style="width:90px;height:90px;object-fit:cover;border-radius:10px;border:1px solid #2a1a1e;display:block" /></a></td>'
            product_block = f'''<table cellpadding="0" cellspacing="0" width="100%" style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;margin:24px 0">
            <tr><td style="padding:18px">
            <table cellpadding="0" cellspacing="0" width="100%"><tr>
            {img_cell}
            <td style="vertical-align:middle">
            <p style="margin:0 0 2px;color:#777!important;font-size:9px;font-weight:700;letter-spacing:3px;text-transform:uppercase">YOUR ORDER</p>
            <p style="margin:0 0 6px;color:#fff;font-size:15px;font-weight:700;line-height:1.3">{prod_name}</p>
            {'<p style="margin:0 0 8px;color:#c9a227;font-size:18px;font-weight:800">'+prod_total+' '+prod_currency+'</p>' if prod_total else ''}
            <a href="{SITE_URL}" style="color:#c9a227;font-size:11px;text-decoration:none;font-weight:700;letter-spacing:1px">VISIT STORE &rarr;</a>
            </td></tr></table>
            </td></tr></table>'''

        status_msg = STATUS_MESSAGES.get(new_status, STATUS_MESSAGES['new'])
        
        body_html = f'''<p style="color:#aaa!important;font-size:15px;line-height:1.8;margin:0 0 20px;text-align:center">Hi <strong style="color:#fff">{safe_get(row,'shipping_name','there')}</strong>,</p>
        <p style="color:#aaa!important;font-size:15px;line-height:1.8;margin:0 0 24px;text-align:center">{status_msg['body']}</p>
        <table cellpadding="0" cellspacing="0" width="100%" style="margin:0 0 24px"><tr><td align="center">
        <table cellpadding="0" cellspacing="0" style="background-color:#1a1014;border:1px solid #2a1a1e;border-radius:10px;min-width:280px">
        <tr><td style="padding:24px 40px;text-align:center">
        <p style="margin:0 0 8px;font-size:40px;line-height:1">{s['icon']}</p>
        <p style="margin:0 0 4px;color:{s['color']};font-size:20px;font-weight:800;letter-spacing:0.5px">{status_msg['heading']}</p>
        <p style="margin:0;color:#666!important;font-size:10px;letter-spacing:1px;text-transform:uppercase">Order #{safe_get(row,'order_number')}</p>
        </td></tr></table>
        </td></tr></table>
        {product_block}'''
        if tracking:
            body_html += f'''<table cellpadding="0" cellspacing="0" width="100%" style="background-color:#1a1014 !important;border:1px solid #2a1a1e;border-radius:10px;margin:0 0 24px">
            <tr><td style="padding:16px 18px">
            <p style="margin:0 0 6px;color:#777777 !important;font-size:9px;font-weight:700;letter-spacing:2px;text-transform:uppercase">TRACKING NUMBER</p>
            <p style="margin:0;color:#fff;font-size:17px;font-weight:800;letter-spacing:1px">{tracking}</p>
            </td></tr></table>'''
        
        # Use custom content if provided
        if custom_body.strip():
            body_html = f'<div style="color:#ccc;font-size:15px;line-height:1.7;white-space:pre-wrap">{custom_body}</div>'
            body_html += product_block
            if tracking:
                body_html += f'<div style="background:rgba(201,162,39,.05);border:1px solid #2a1a1e;border-radius:8px;padding:15px;margin:15px 0 0"><p style="margin:0;color:#c9a227;font-size:11px;font-weight:700;letter-spacing:2px">TRACKING</p><p style="margin:5px 0 0;color:#fff;font-size:16px;font-weight:700">{tracking} ({carrier})</p></div>'
        
        email_subject = custom_subject.strip() if custom_subject.strip() else f'Order #{safe_get(row,"order_number")} — {status_msg["subject"]}'
        
        # Only show tracking button if tracking exists, otherwise show "Visit Store" for early statuses or nothing
        if tracking_btn_text and tracking_btn_url:
            btn_text = tracking_btn_text
            btn_url = tracking_btn_url
        elif new_status in ('shipped_china', 'in_romania', 'sent_cargus', 'delivered'):
            btn_text = 'TRACK YOUR ORDER'
            btn_url = f'{SITE_URL}/pages/track-your-order'
        elif new_status in ('new', 'ordered', 'warehouse'):
            btn_text = ''
            btn_url = ''
        else:
            btn_text = 'VISIT OUR STORE'
            btn_url = SITE_URL
        
        send_email(email, email_subject,
                   email_template('VEXORA MAISON', status_msg['heading'], body_html, btn_text, btn_url))
    
    db.close()
    return redirect(f'/admin?pw={pw}')

# ===================== ADMIN SEARCH PRODUCTS (WooCommerce proxy) =====================
@app.route('/admin/search-products')
def admin_search_products():
    pw = request.args.get('pw', '')
    if pw != DASH_PASS:
        return jsonify([])
    q = request.args.get('q', '').strip().lower()
    if len(q) < 2:
        return jsonify([])
    try:
        # Use WooCommerce REST API
        r = requests.get(f'{WC_URL}/wp-json/wc/v3/products', params={
            'consumer_key': WC_KEY, 'consumer_secret': WC_SECRET,
            'search': q, 'per_page': 10, 'status': 'publish'
        }, timeout=10)
        products = r.json() if r.status_code == 200 else []
        results = []
        for p in products:
            title = p.get('name', '')
            if q not in title.lower():
                continue
            img = ''
            images = p.get('images', [])
            if images:
                img = images[0].get('src', '')
            price = p.get('price', '0')
            try:
                price = f"{float(price):.2f} EUR"
            except:
                price = str(price) + ' EUR'
            results.append({
                'title': title,
                'image': img,
                'price': price,
                'url': p.get('permalink', '')
            })
            if len(results) >= 6:
                break
        return jsonify(results)
    except Exception as e:
        print(f'Product search error: {e}')
        return jsonify([])

# ===================== ADMIN ADD MANUAL ORDER =====================
@app.route('/admin/add-order', methods=['POST'])
def admin_add_order():
    pw = request.form.get('pw', '')
    if pw != DASH_PASS:
        return redirect('/admin')
    
    now = datetime.datetime.now().isoformat()
    order_number = 'M' + datetime.datetime.now().strftime('%m%d%H%M%S')
    
    shipping_name = request.form.get('shipping_name', '').strip()
    customer_email = request.form.get('customer_email', '').strip()
    product_name = request.form.get('product_name', '').strip()
    
    if not shipping_name or not customer_email or not product_name:
        print(f'Manual order validation failed: name={shipping_name}, email={customer_email}, product={product_name}')
        return redirect(f'/admin?pw={pw}')
    
    timeline = json.dumps([{'status': 'New Order (Manual)', 'date': now, 'icon': '📥', 'color': '#3b82f6', 'note': 'Manually added via dashboard'}])
    
    try:
        db = get_db()
        db.execute('''INSERT INTO orders(order_id, order_number, product_name, product_url, 
            customer_email, shipping_name, shipping_address, shipping_city, shipping_zip, 
            shipping_phone, total, currency, status, created_at, updated_at, timeline) 
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            ('manual_' + order_number, order_number, product_name, 
             request.form.get('product_url', ''),
             customer_email, shipping_name,
             request.form.get('shipping_address', ''),
             request.form.get('shipping_city', ''),
             '', request.form.get('shipping_phone', ''),
             request.form.get('total', '0'), request.form.get('currency', 'RON'),
             'new', now, now, timeline))
        db.commit()
        db.close()
        print(f'SUCCESS: Manual order #{order_number} — {product_name} for {shipping_name} ({customer_email})')
        return redirect(f'/admin?pw={pw}')
    except Exception as e:
        print(f'FAILED: Manual order error: {e}')
        try:
            db.close()
        except:
            pass
        return redirect(f'/admin?pw={pw}')

# ===================== UNSUBSCRIBE =====================
@app.route('/unsubscribe')
def unsubscribe():
    email = request.args.get('email', '').strip()
    if email:
        db = get_db()
        db.execute("UPDATE subscribers SET status='unsubscribed' WHERE email=?", (email,))
        db.commit()
        db.close()
    return f'''<html><body style="background:#0f0609;color:#fff;font-family:Helvetica,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center">
    <div><h2 style="color:#c9a227;margin-bottom:15px">Dezabonat cu succes</h2>
    <p style="color:#888">Nu vei mai primi newslettere de la Vexora Maison.</p>
    <p style="margin-top:20px"><a href="{SITE_URL}" style="color:#c9a227">Înapoi la magazin</a></p></div></body></html>'''

# ===================== ADMIN NEWSLETTER SEND =====================
@app.route('/admin/newsletter', methods=['POST'])
def admin_newsletter():
    pw = request.form.get('pw', '')
    if pw != DASH_PASS:
        return redirect('/admin')
    action = request.form.get('action', '')
    
    if action == 'custom':
        subject = request.form.get('nl_subject', '').strip()
        body_text = request.form.get('nl_body', '').strip()
        if subject and body_text:
            body_html = f'<p style="color:#ccc;font-size:15px;line-height:1.7;white-space:pre-wrap">{body_text}</p>'
            sent = send_newsletter_bulk(custom_subject=subject, custom_body=body_html)
            return redirect(f'/admin?pw={pw}&tab=subscribers&sent={sent}')
    elif action == 'template':
        tpl_id = request.form.get('template_id', '')
        sent = send_newsletter_bulk(template_id=tpl_id)
        return redirect(f'/admin?pw={pw}&tab=subscribers&sent={sent}')
    
    return redirect(f'/admin?pw={pw}&tab=subscribers')

# ===================== ADMIN ADD SUBSCRIBER MANUALLY =====================
@app.route('/admin/add-subscriber', methods=['POST'])
def admin_add_subscriber():
    pw = request.form.get('pw', '')
    if pw != DASH_PASS:
        return redirect('/admin')
    
    raw = request.form.get('emails', '')
    # Split by newlines, commas, semicolons, spaces
    emails = []
    for line in raw.replace(',', '\n').replace(';', '\n').split('\n'):
        e = line.strip().lower()
        if e and '@' in e and '.' in e:
            emails.append(e)
    
    if not emails:
        return redirect(f'/admin?pw={pw}&tab=subscribers')
    
    now = datetime.datetime.now().isoformat()
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS subscribers(
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE,
        subscribed_at TEXT, status TEXT DEFAULT 'active')''')
    
    added = 0
    for email in emails:
        try:
            db.execute('INSERT INTO subscribers(email, subscribed_at, status) VALUES(?,?,?)', (email, now, 'active'))
            added += 1
        except:
            # Already exists — reactivate if unsubscribed
            db.execute("UPDATE subscribers SET status='active' WHERE email=? AND status='unsubscribed'", (email,))
    
    db.commit()
    db.close()
    print(f'Manually added {added} subscribers (from {len(emails)} emails)')
    return redirect(f'/admin?pw={pw}&tab=subscribers&added={added}')

# ===================== ADMIN SEND DIRECT EMAIL =====================
@app.route('/admin/send-direct', methods=['POST'])
def admin_send_direct():
    pw = request.form.get('pw', '')
    if pw != DASH_PASS:
        return redirect('/admin')
    
    raw_to = request.form.get('to_emails', '')
    subject = request.form.get('direct_subject', '').strip()
    body_text = request.form.get('direct_body', '').strip()
    btn_text = request.form.get('direct_btn_text', '').strip()
    also_subscribe = request.form.get('also_subscribe', '')
    
    # Parse emails
    to_emails = []
    for line in raw_to.replace(',', '\n').replace(';', '\n').split('\n'):
        e = line.strip().lower()
        if e and '@' in e:
            to_emails.append(e)
    
    if not to_emails or not subject or not body_text:
        return redirect(f'/admin?pw={pw}&tab=subscribers')
    
    # Build HTML body
    body_html = f'<p style="color:#ccc;font-size:15px;line-height:1.7;white-space:pre-wrap">{body_text}</p>'
    
    sent = 0
    for email in to_emails:
        html = email_template('VEXORA MAISON', 'Vexora Maison', body_html, 
                              btn_text if btn_text else 'SHOP NOW', SITE_URL)
        if send_email(email, subject, html):
            sent += 1
    
    # Also add to subscribers if checked
    if also_subscribe:
        now = datetime.datetime.now().isoformat()
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS subscribers(
            id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE,
            subscribed_at TEXT, status TEXT DEFAULT 'active')''')
        for email in to_emails:
            try:
                db.execute('INSERT INTO subscribers(email, subscribed_at, status) VALUES(?,?,?)', (email, now, 'active'))
            except:
                db.execute("UPDATE subscribers SET status='active' WHERE email=? AND status='unsubscribed'", (email,))
        db.commit()
        db.close()
    
    print(f'Direct email sent to {sent}/{len(to_emails)} recipients. Subject: {subject}')
    return redirect(f'/admin?pw={pw}&tab=subscribers&sent={sent}')

# ===================== AUTO NEWSLETTER CRON =====================
@app.route('/cron/newsletter')
def cron_newsletter():
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS newsletter_log(id INTEGER PRIMARY KEY AUTOINCREMENT, template_id TEXT, subject TEXT, sent_at TEXT, recipients INTEGER, status TEXT)''')
    last = db.execute("SELECT sent_at FROM newsletter_log ORDER BY sent_at DESC LIMIT 1").fetchone()
    db.close()
    
    if last and last['sent_at']:
        last_date = datetime.datetime.fromisoformat(last['sent_at'])
        days_since = (datetime.datetime.now() - last_date).days
        if days_since < AUTO_NEWSLETTER_DAYS:
            return jsonify({'status': 'skipped', 'days_since_last': days_since, 'next_in': AUTO_NEWSLETTER_DAYS - days_since})
    
    sent = send_newsletter_bulk()
    return jsonify({'status': 'sent', 'recipients': sent})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f'\n  Vexora Admin v6 (WooCommerce) — port {port}\n')
    app.run(host='0.0.0.0', port=port, debug=False)