s = open("app.py").read()
old = """    total_scheduled = UploadJob.query.join(PostingChannel).filter(PostingChannel.user_id == uid, UploadJob.status == "scheduled").count()
    total_uploaded = UploadJob.query.join(PostingChannel).filter(PostingChannel.user_id == uid, UploadJob.status == "uploaded").count()
    return render_template("dashboard.html", categories=CATEGORIES, by_category=by_category, total_scheduled=total_scheduled, total_uploaded=total_uploaded)"""
new = """    total_scheduled = UploadJob.query.join(PostingChannel).filter(PostingChannel.user_id == uid, UploadJob.status == "scheduled").count()
    total_uploaded = UploadJob.query.join(PostingChannel).filter(PostingChannel.user_id == uid, UploadJob.status == "uploaded").count()
    return render_template("dashboard.html", categories=CATEGORIES, by_category=by_category, total_scheduled=total_scheduled, total_uploaded=total_uploaded, schedule_url="/schedule")"""
open("app.py","w").write(s.replace(old,new))
print("Done!" if old in s else "NOT FOUND")

