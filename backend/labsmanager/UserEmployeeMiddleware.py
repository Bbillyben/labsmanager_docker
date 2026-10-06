

class UserEmployeeMiddleware(object):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.user.is_authenticated():
            from staff.models import Employee
            emp = Employee.objects.filter(user=request.user)
            if emp:
                request.user.employee = emp.first()
