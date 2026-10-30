def recommend(attendance, intervals, audio):
    suggestions = []
    if not intervals:
        return [{'type':'Data quality','observation':'No usable intervals','reason':'The video did not yield sampled frames.','suggestion':'Check the video format and try a clear, steady recording.'}]
    vals = [x['engagement'] for x in intervals]
    avg = sum(vals)/len(vals)
    low = [x for x in intervals if x['engagement'] < 35]
    if low:
        x=low[0]; suggestions.append({'type':'Low activity','observation':f"Low estimated activity around {int(x['start_seconds']//60)} min",'reason':'The combined presence, motion and audio indicators were low in this interval.','suggestion':'Consider asking a question or adding a brief interactive activity; check whether the camera view affected the signals.'})
    if len(vals)>1 and max(vals)-min(vals)>25:
        peak=max(intervals,key=lambda x:x['engagement']); suggestions.append({'type':'Session dynamics','observation':f"Activity peak around {int(peak['start_seconds']//60)} min",'reason':'Estimated activity varied noticeably across intervals.','suggestion':'Review this portion of the session and note what format or topic may have supported participation.'})
    if audio and audio['activity_fraction'] < .1:
        suggestions.append({'type':'Audio activity','observation':'Little audio energy detected','reason':'Measured signal activity was below 10%; quiet instruction, microphone placement, or muted audio can explain this.','suggestion':'Check microphone placement and use verbal check-ins where appropriate.'})
    present=sum(x['status']=='Present' for x in attendance)
    if not suggestions:
        suggestions.append({'type':'Session summary','observation':f'Average estimated engagement indicator: {avg:.0f}/100','reason':'No interval crossed the configured low-activity threshold.','suggestion':'Use these aggregate indicators alongside your own observations when planning the next session.'})
    return suggestions
