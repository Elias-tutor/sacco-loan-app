from flask import Flask, render_template, request, send_file, redirect, url_for
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
import os
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('templates', exist_ok=True)

world_bank_loans = []

@app.route('/')
def index():
    return render_template('world_bank_index.html', members=world_bank_loans)

@app.route('/add_wb_member', methods=['POST'])
def add_wb_member():
    member_name = request.form.get('member_name')
    sex = request.form.get('sex')
    contact = request.form.get('contact')
    place = request.form.get('place')
    business_type = request.form.get('business_type')
    principal = float(request.form.get('principal'))
    loan_date_str = request.form.get('loan_date')
    
    photo = request.files.get('photo')
    photo_filename = "default.jpg"
    if photo and photo.filename != '':
        photo_filename = f"{random.randint(1000,9999)}_{photo.filename}"
        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
        
    loan_date = datetime.strptime(loan_date_str, '%Y-%m-%d')
    loan_id = f"WB-NMVS-{random.randint(100, 999)}.{loan_date.strftime('%Y')}"
    
    app_fee = 10000
    sub_fee = 10000
    proc_fee = 5000
    initial_deposit = principal * 0.05
    compulsory_weekly_saving = 5000
    
    # 3-Month Weekly Reducing Balance Schedule (12 weeks)
    r = 0.0125  # ~5% monthly rate / 4 weeks
    total_weeks = 12
    weekly_installment = principal * (r * (1 + r)**total_weeks) / ((1 + r)**total_weeks - 1)
    
    total_interest_paid = 0
    balance = principal
    schedule = []
    
    for week in range(1, total_weeks + 1):
        interest_due = balance * r
        principal_due = weekly_installment - interest_due
        balance -= principal_due
        if balance < 0: balance = 0.0
        
        total_interest_paid += interest_due
        payment_date = loan_date + timedelta(days=(7 * week))
        
        schedule.append({
            'week': week,
            'date': payment_date.strftime('%Y-%m-%d'),
            'principal_due': round(principal_due, 2),
            'interest_due': round(interest_due, 2),
            'compulsory_saving': compulsory_weekly_saving,
            'total_due': round(weekly_installment + compulsory_weekly_saving, 2),
            'balance': round(balance, 2),
            'status': ''
        })
        
    total_comp_savings = compulsory_weekly_saving * total_weeks
    
    member_data = {
        'loan_id': loan_id,
        'member_name': member_name,
        'sex': sex,
        'contact': contact,
        'place': place,
        'business_type': business_type,
        'principal': principal,
        'loan_date': loan_date_str,
        'photo': photo_filename,
        'app_fee': app_fee,
        'sub_fee': sub_fee,
        'proc_fee': proc_fee,
        'initial_deposit': initial_deposit,
        'total_interest': round(total_interest_paid, 2),
        'total_comp_savings': total_comp_savings,
        'total_expected': round(principal + total_interest_paid + app_fee + sub_fee + proc_fee + total_comp_savings, 2),
        'schedule': schedule
    }
    
    world_bank_loans.append(member_data)
    return redirect(url_for('index'))

@app.route('/clear_wb_members', methods=['POST'])
def clear_wb_members():
    world_bank_loans.clear()
    return redirect(url_for('index'))

@app.route('/download_wb_schedule/<loan_id>')
def download_wb_schedule(loan_id):
    member = next((m for m in world_bank_loans if m['loan_id'] == loan_id), None)
    if not member: return redirect(url_for('index'))
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    logo_path = os.path.join('templates', 'nyakadote mvs logo .jpg')
    if os.path.exists(logo_path):
        try:
            logo = RLImage(logo_path, width=45, height=45)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 4))
        except: pass
        
    h_style = ParagraphStyle('HS', parent=styles['Heading1'], fontSize=11, alignment=1, textColor=colors.HexColor('#1a365d'))
    sh_style = ParagraphStyle('SHS', parent=styles['Normal'], fontSize=8.5, alignment=1, textColor=colors.HexColor('#4a5568'))
    
    story.append(Paragraph("NYAKADOTE MARKET VENDORS SAVINGS AND CREDIT SOCIETY", h_style))
    story.append(Paragraph("REG. NO: 11880/RCS | Bweyale Town Council, Kiryandongo District", sh_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("WORLD BANK FINANCED LOAN REPAYMENT SCHEDULE (WEEKLY REDUCING)", ParagraphStyle('T', parent=styles['Heading2'], fontSize=9.5, alignment=1, textColor=colors.HexColor('#2b6cb0'))))
    story.append(Spacer(1, 6))
    
    photo_full_path = os.path.join(app.config['UPLOAD_FOLDER'], member['photo'])
    img_element = RLImage(photo_full_path, width=45, height=45) if os.path.exists(photo_full_path) else Paragraph("No Photo", styles['Normal'])
    
    details_data = [
        [Paragraph(f"<b>Member Name:</b> {member['member_name']}", styles['Normal']), Paragraph(f"<b>Loan ID:</b> {member['loan_id']}", styles['Normal']), img_element],
        [Paragraph(f"<b>Sex/Place:</b> {member['sex']} / {member['place']}", styles['Normal']), Paragraph(f"<b>Contact:</b> {member['contact']}", styles['Normal']), Paragraph(f"<b>Business:</b> {member['business_type']}", styles['Normal'])],
        [Paragraph(f"<b>Principal Loan:</b> UGX {member['principal']:,.2f}", styles['Normal']), Paragraph(f"<b>Loan Date:</b> {member['loan_date']}", styles['Normal']), Paragraph(f"<b>Initial Deposit (5%):</b> UGX {member['initial_deposit']:,.2f}", styles['Normal'])]
    ]
    details_table = Table(details_data, colWidths=[200, 180, 160])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f7fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 4),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 8))
    
    table_data = [["Wk", "Date", "Principal", "Interest (1.25%w)", "Comp. Save", "Total Due", "Balance", "Status"]]
    for row in member['schedule']:
        table_data.append([
            str(row['week']),
            row['date'],
            f"{row['principal_due']:,.2f}",
            f"{row['interest_due']:,.2f}",
            f"{row['compulsory_saving']:,.2f}",
            f"{row['total_due']:,.2f}",
            f"{row['balance']:,.2f}",
            ""
        ])
    sched_table = Table(table_data, colWidths=[30, 75, 75, 95, 70, 75, 75, 45])
    sched_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2b6cb0')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f7fafc')]),
        ('PADDING', (0,0), (-1,-1), 3.5),
        ('FONTSIZE', (0,1), (-1,-1), 7.5),
    ]))
    story.append(sched_table)
    story.append(Spacer(1, 8))
    
    total_fees = member['app_fee'] + member['sub_fee'] + member['proc_fee']
    
    summary_data = [
        [Paragraph("<b>Principal Loan Amount:</b>", styles['Normal']), Paragraph(f"UGX {member['principal']:,.2f}", styles['Normal'])],
        [Paragraph("<b>Total Interest (Reducing Balance):</b>", styles['Normal']), Paragraph(f"UGX {member['total_interest']:,.2f}", styles['Normal'])],
        [Paragraph("<b>Fees Paid (App: 10k, Sub: 10k, Proc: 5k):</b>", styles['Normal']), Paragraph(f"UGX {total_fees:,.2f}", styles['Normal'])],
        [Paragraph("<b>Compulsory Savings (12 Weeks @ 5k):</b>", styles['Normal']), Paragraph(f"UGX {member['total_comp_savings']:,.2f}", styles['Normal'])],
        [Paragraph("<b>Expected Total Repayment:</b>", styles['Normal']), Paragraph(f"<b>UGX {member['total_expected']:,.2f}</b>", styles['Normal'])],
    ]
    summary_table = Table(summary_data, colWidths=[280, 260])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#edf2f7')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e0')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    story.append(summary_table)
    
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{member['member_name']}_WB_Schedule.pdf", mimetype='application/pdf')

@app.route('/download_loans_given_report')
def download_loans_given_report():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    h_style = ParagraphStyle('HS', parent=styles['Heading1'], fontSize=13, alignment=1, textColor=colors.HexColor('#1a365d'))
    sh_style = ParagraphStyle('SHS', parent=styles['Normal'], fontSize=9.5, alignment=1, textColor=colors.HexColor('#4a5568'))
    
    story.append(Paragraph("NYAKADOTE MARKET VENDORS SAVINGS AND CREDIT SOCIETY", h_style))
    story.append(Paragraph("REG. NO: 11880/RCS | Bweyale Town Council, Kiryandongo District", sh_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("SUMMARY REPORT: ALL APPROVED LOANS GIVEN OUT (APPLICANTS QUEUE)", ParagraphStyle('T', parent=styles['Heading2'], fontSize=11, alignment=1, textColor=colors.HexColor('#2b6cb0'))))
    story.append(Spacer(1, 10))
    
    table_data = [["No.", "Loan ID", "Member Name", "Sex", "Contact", "Place / Village", "Business Type", "Principal (UGX)", "5% Deposit (UGX)", "Loan Date"]]
    
    total_principal = 0
    total_deposit = 0
    
    for idx, m in enumerate(world_bank_loans, 1):
        total_principal += m['principal']
        total_deposit += m['initial_deposit']
        table_data.append([
            str(idx),
            m['loan_id'],
            m['member_name'],
            m['sex'],
            m['contact'],
            m['place'],
            m['business_type'],
            f"{m['principal']:,.2f}",
            f"{m['initial_deposit']:,.2f}",
            m['loan_date']
        ])
        
    table_data.append([
        "TOTAL", "", "", "", "", "", "", 
        f"{total_principal:,.2f}", 
        f"{total_deposit:,.2f}", 
        ""
    ])
    
    report_table = Table(table_data, colWidths=[30, 95, 130, 45, 80, 90, 110, 85, 85, 70])
    report_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2b6cb0')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f7fafc')]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#edf2f7')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('PADDING', (0,0), (-1,-1), 4),
        ('FONTSIZE', (0,1), (-1,-1), 8),
    ]))
    story.append(report_table)
    
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="Nyakadote_Loans_Given_Out_Report.pdf", mimetype='application/pdf')

@app.route('/profit_report')
def profit_report():
    wb_principal = 15000000
    wb_annual_rate = 0.05
    wb_years = 2
    wb_total_interest = wb_principal * wb_annual_rate * wb_years  # 1,500,000 UGX
    wb_total_repayment = wb_principal + wb_total_interest            # 16,500,000 UGX
    
    quarterly_data = []
    total_cycle_interest = 18000000
    total_fees = 2500000
    total_savings = 4800000
    
    for i in range(1, 9):
        quarterly_data.append({
            'quarter': f"Q{i} (Year {(i-1)//4 + 1})",
            'interest': 2250000,
            'fees': 312500,
            'savings': 600000,
            'total_inflow': 3162500
        })
        
    gross_revenue = total_cycle_interest + total_fees
    net_profit = gross_revenue - wb_total_interest # 19,000,000 UGX
    
    return render_template('profit_report.html', 
                           wb_principal=wb_principal,
                           wb_total_interest=wb_total_interest,
                           wb_total_repayment=wb_total_repayment,
                           gross_revenue=gross_revenue,
                           net_profit=net_profit,
                           total_savings=total_savings,
                           quarterly_data=quarterly_data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)