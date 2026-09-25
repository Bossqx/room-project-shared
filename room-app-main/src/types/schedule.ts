export interface Teacher {
  officerid:      string
  officerlogin:   string
  prefixname:     string
  officername:    string
  officersurname: string
}

export interface ScheduleItem {
  schedule_id:number;
  roomcode:       string
  coursecode:     string
  coursename:     string
  weekday:        string
  timeperiodfrom: string
  timeperiodto:   string
  startTime:      string
  finishTime:     string
  teacher:        Teacher[]
  uuid?:          string
  isExist:boolean
  objective:string 
}

export interface ScheduleItemDB {
  schedule_id:number
  roomcode:       string
  coursecode:     string
  coursename:     string
  weekday:        string
  timeperiodfrom: string
  timeperiodto:   string
  startTime:      string
  finishTime:     string
  teacher_name:   string
  schedule_date?: string
  uuid?:          string
  isExist?:       boolean
  objective:string 
}
