def message_response(message, code=None, orther_message=None):
    context = {
        'message': message
    }
    if code:
        context.update({'code':code})
    if orther_message:
        context.update({'info':orther_message})
    return context
