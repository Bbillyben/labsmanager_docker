import rules



#    Rules ======================
from staff.rules import is_team_leader
rules.add_perm('leave.change_leave', is_team_leader)