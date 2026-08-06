def summarize_event(event): return event.description[:500]
def check_missing_fields(event):
    missing=[]
    for field in ("title","description","due_date","device_lot"):
        if not getattr(event,field,None): missing.append(field)
    if not hasattr(event,"investigation"): missing.append("investigation")
    if not event.capas.exists(): missing.append("capa")
    if not event.approvals.exists(): missing.append("approver")
    return missing
def generate_report_draft(event): return {"summary":summarize_event(event),"missing_fields":check_missing_fields(event)}
