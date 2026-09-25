import { ref } from 'vue'

export type AppLocale = 'th' | 'en'

const STORAGE_KEY = 'room-app-locale'

function initialLocale(): AppLocale {
  const saved = localStorage.getItem(STORAGE_KEY)
  return saved === 'en' ? 'en' : 'th'
}

export const locale = ref<AppLocale>(initialLocale())

/**
 * The application originally shipped with text embedded directly in many Vue
 * views.  Keeping this catalogue at the application boundary lets every
 * existing screen participate in the language switch without duplicating
 * locale state in each view. New screens should add their copy here.
 */
const translations: Array<readonly [thai: string, english: string]> = [
  ['ระบบบริหารจัดการห้องคอมพิวเตอร์สำนักคอมพิวเตอร์', 'Computer Room Management System — Computer Center'],
  ['ระบบจองห้องและแสดงตารางการใช้ห้องคอมพิวเตอร์', 'Computer Room Booking and Schedule System'],
  ['ระบบบริหารจัดการห้องคอมพิวเตอร์', 'Computer Room Management System'],
  ['ระบบบริหารจัดการห้อง © มหาวิทยาลัยราชภัฏนครราชสีมา', 'Room Management System © Nakhon Ratchasima Rajabhat University'],
  ['ระบบบริหารจัดการห้อง', 'Room Management System'],
  ['ระบบจองห้องคอมพิวเตอร์', 'Computer Room Booking System'],
  ['มหาวิทยาลัยราชภัฏนครราชสีมา', 'Nakhon Ratchasima Rajabhat University'],
  ['ตราสัญลักษณ์ระบบบริหารจัดการห้องคอมพิวเตอร์', 'Computer room management system logo'],
  ['ตราสัญลักษณ์ระบบบริหารจัดการห้อง', 'Room management system logo'],
  ['ตราสัญลักษณ์ระบบ', 'System logo'],

  ['สถานะห้องแบบ Real-time', 'Real-time Room Status'],
  ['สถานะห้องแบบเรียลไทม์', 'Real-time Room Status'],
  ['ตารางการใช้ห้องประจำสัปดาห์', 'Weekly Room Schedule'],
  ['ตรวจสอบตารางการใช้ห้อง', 'Room Schedule Enquiry'],
  ['ยืนยันการยกเลิกการใช้ห้องหรือไม่', 'Cancel this room session?'],
  ['ยืนยันการเข้าใช้งานหรือไม่', 'Confirm room usage?'],
  ['ยืนยันการลบตารางหรือไม่', 'Delete this schedule?'],
  ['ส่วนยืนยันการเข้าใช้งานยังไม่พร้อมใช้งานชั่วคราว', 'The confirmation panel is temporarily unavailable.'],
  ['ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง', 'The username or password is incorrect'],
  ['โปรดตรวจสอบชื่อผู้ใช้และรหัสผ่าน แล้วลองอีกครั้ง', 'Check your username and password, then try again.'],
  ['ใช้รหัสพินนี้เพื่อยืนยันการเข้าใช้งานห้อง และสามารถเปลี่ยนได้ภายหลังจากเมนูรหัสพิน', 'Use this PIN to confirm room access. You can change it later from the PIN menu.'],
  ['รหัสพินสำหรับเข้าใช้งานห้อง', 'Your Room Access PIN'],
  ['เข้าสู่ระบบบัญชีของคุณ', 'Sign in to your account'],
  ['ไม่สามารถเชื่อมต่อกับระบบได้', 'Cannot connect to the system'],
  ['เข้าสู่ระบบไม่สำเร็จ', 'Sign in failed'],
  ['รหัสพินใหม่ต้องมีอย่างน้อย 6 หลัก', 'The new PIN must contain at least 6 digits'],
  ['รหัสพินทั้งสองช่องไม่ตรงกัน', 'The PINs do not match'],
  ['เปลี่ยนรหัสพินสำเร็จ', 'PIN changed successfully'],
  ['ไม่สามารถเปลี่ยนรหัสพินได้', 'Failed to change PIN'],
  ['ตั้งรหัสพินใหม่สำหรับ', 'Set a new PIN for'],
  ['ยืนยันการเข้าใช้แล้ว', 'Room usage confirmed'],
  ['ยกเลิกการใช้ห้องสำเร็จ', 'Room usage cancelled'],
  ['จองห้องสำเร็จ', 'Room booked successfully'],
  ['ลบตารางสำเร็จ', 'Schedule deleted'],

  ['แดชบอร์ดสถานะและการใช้ห้องคอมพิวเตอร์', 'Computer Room Status and Usage Dashboard'],
  ['ภาพรวมสถานะห้อง', 'Room Status Overview'],
  ['สรุปข้อมูลวันนี้', "Today's Summary"],
  ['ห้องทั้งหมด', 'Total Rooms'],
  ['ข้อมูลห้องในระบบ', 'Rooms registered in the system'],
  ['ห้องว่างตอนนี้', 'Rooms Available Now'],
  ['พร้อมใช้งาน', 'Ready to use'],
  ['จากสถานะยืนยัน', 'Based on confirmed usage'],
  ['ตารางสอนวันนี้', "Today's Schedule"],
  ['ตารางสอนวันที่เลือก', 'Schedule for Selected Date'],
  ['รวมทุกห้องวันนี้', 'All rooms today'],
  ['รวมทุกห้องในวันนั้น', 'All rooms on that date'],
  ['กำลังแสดงมุมมอง', 'Currently showing'],
  ['เวลาปัจจุบัน', 'Current time'],
  ['คำอธิบายสถานะ', 'Status legend'],
  ['ว่าง ใช้งาน มีตาราง ไม่มีข้อมูล', 'Available · In use · Scheduled · No data'],
  ['กำลังโหลดสถานะห้อง…', 'Loading room status…'],
  ['ไม่ระบุชั้น', 'Floor not specified'],
  ['มีตาราง—ยังไม่ยืนยัน', 'Scheduled — awaiting confirmation'],
  ['มีตารางวันนี้', 'Scheduled today'],
  ['ไม่มีข้อมูลสถานะ', 'Status unavailable'],
  ['ไม่มีรายการถัดไปวันนี้', 'No more entries today'],
  ['ไม่มีรายการ', 'No entries'],
  ['กำลังเชื่อมต่อข้อมูล', 'Connecting to data…'],
  ['ไม่สามารถโหลดข้อมูลซอฟต์แวร์และอุปกรณ์ได้', 'Unable to load software and equipment information'],
  ['ไม่สามารถโหลดข้อมูลสถานะห้องแบบเรียลไทม์ได้', 'Unable to load real-time room status'],
  ['รายการที่ผ่านมาแล้ว', 'Past entry'],

  ['ตารางการจอง', 'Booking Schedule'],
  ['ตารางการจองห้อง', 'Room Booking Schedule'],
  ['เลือกห้องเพื่อดูช่วงเวลาว่างและจองได้ทันที', 'Select a room to view availability and book immediately'],
  ['ดูตารางการใช้ห้องทั้งหมดในสัปดาห์เดียวกัน', 'View all room schedules for the selected week'],
  ['เปรียบเทียบตารางและช่วงเวลาว่างของทุกห้องในวันที่เลือก', 'Compare schedules and availability for every room on the selected date'],
  ['ดูตารางทุกห้องครบทั้ง 7 วันภายในสัปดาห์เดียวกัน', 'View every room schedule across all seven days of the selected week'],
  ['ตารางทุกห้องประจำวัน', 'Daily Schedule for All Rooms'],
  ['ตารางทุกห้องประจำสัปดาห์', 'Weekly Schedule for All Rooms'],
  ['ไม่พบห้องที่ตรงกับตัวกรอง', 'No rooms match the selected filters'],
  ['ดูตามห้อง', 'Room View'],
  ['แดชบอร์ด', 'Dashboard'],
  ['แดชบอร์ดใหม่', 'New Dashboard'],
  ['นำเข้าข้อมูล', 'Migration'],
  ['ภาคการศึกษา', 'Semester'],
  ['ภาคการศึกษาทั้งหมด', 'Semesters'],
  ['เพิ่มภาคการศึกษา', 'Add Semester'],
  ['รายการห้อง', 'Rooms'],
  ['ยกเลิกห้อง', 'Cancel Room'],
  ['ผู้ดูแลระบบ', 'Admin'],
  ['ตารางการใช้ห้อง', 'Room Schedule'],
  ['ตารางประจำสัปดาห์', 'Weekly Schedule'],
  ['ตารางปัจจุบัน', 'Current Schedule'],
  ['ตารางรวม', 'All Schedules'],
  ['ทั้งสัปดาห์', 'Full Week'],
  ['รูปแบบการแสดงตาราง', 'Schedule View'],
  ['แยกตามห้อง', 'Room View'],
  ['สถานะการใช้ห้อง', 'Room Usage Status'],
  ['สถานะห้อง', 'Room Status'],
  ['รายละเอียดห้อง', 'Room Details'],
  ['โปรแกรมที่ติดตั้ง', 'Installed Software'],
  ['รูปภาพห้องทั้งหมด', 'All Room Photos'],
  ['ไม่มีรูปห้องในข้อมูลปัจจุบัน', 'No room photos are currently available'],
  ['ไม่มีข้อมูลประเภทห้อง', 'Room type unavailable'],
  ['ไม่มีข้อมูลโปรแกรม', 'No software information'],
  ['ไม่มีข้อมูลอุปกรณ์', 'No equipment information'],
  ['ไม่มีข้อมูลห้องในระบบ', 'No rooms are available in the system'],
  ['ไม่มีรายการในวันปัจจุบัน', 'No entries for today'],
  ['ไม่มีรายการในวันที่เลือก', 'No entries for the selected date'],
  ['ไม่มีตาราง', 'No schedule'],
  ['ว่างทั้งวัน', 'Available All Day'],
  ['ไม่มีข้อมูล', 'No data'],
  ['กำลังโหลดปฏิทินรวม…', 'Loading full calendar…'],
  ['กำลังโหลดตาราง…', 'Loading schedule…'],
  ['กำลังโหลด…', 'Loading…'],
  ['กำลังค้นหา…', 'Searching…'],
  ['กำลังเข้าสู่ระบบ…', 'Signing in…'],
  ['กำลังบันทึก…', 'Saving…'],
  ['กำลังจอง…', 'Booking…'],
  ['กำลังยืนยัน…', 'Confirming…'],
  ['กำลังยกเลิก…', 'Cancelling…'],
  ['กำลังลบ…', 'Deleting…'],
  ['ค้นหาตารางตามห้องและวันที่', 'Search schedules by room and date'],
  ['ยืนยันแล้ว', 'In Use'],
  ['ปิดการใช้งานแล้ว', 'Closed'],

  ['วันที่จอง', 'Booking Date'],
  ['รหัสวิชา / ชื่อวิชา', 'Subject Code / Subject Name'],
  ['รายวิชา / ผู้สอน', 'Subject / Instructor'],
  ['กรอกรหัสวิชาหรือชื่อวิชา', 'Enter a subject code or name'],
  ['รหัสห้อง', 'Room Code'],
  ['กรอกวัตถุประสงค์', 'Enter an objective'],
  ['วัตถุประสงค์', 'Objective'],
  ['เวลาเริ่มต้น', 'Start Time'],
  ['เวลาสิ้นสุด', 'Finish Time'],
  ['— เลือกคาบ —', '— Select a period —'],
  ['เลือกเวลา', 'Select a time'],
  ['กรุณาเข้าสู่ระบบก่อนจองห้อง', 'Please log in before booking a room'],
  ['กรุณาเข้าสู่ระบบ', 'Please log in'],
  ['คุณต้องเข้าสู่ระบบก่อนจึงจะสามารถจองห้องได้', 'You need to log in before booking a room'],
  ['ไปหน้าเข้าสู่ระบบ', 'Go to login'],
  ['ไว้ก่อน', 'Not now'],
  ['ยืนยันการจอง', 'Confirm Booking'],
  ['ยืนยันการเข้าใช้งาน', 'Confirm Room Usage'],
  ['ยืนยันเข้าใช้', 'Confirm Usage'],
  ['ยืนยันการยกเลิก', 'Confirm Cancellation'],
  ['ยกเลิกการใช้ห้อง', 'Cancel Room Usage'],
  ['ยืนยันการลบ', 'Confirm Delete'],
  ['ลบตาราง', 'Delete Schedule'],
  ['ไม่ยกเลิก', 'Keep Session'],
  ['ไว้ภายหลัง', 'Not Now'],
  ['ไม่ลบ', 'Keep Schedule'],
  ['ดำเนินการต่อ', 'Continue'],
  ['ลองอีกครั้ง', 'Try Again'],
  ['ตรวจสอบห้องว่าง', 'Check Empty Rooms'],
  ['ย้อนกลับ', 'Back'],
  ['ถัดไป', 'Next'],
  ['ก่อนหน้า', 'Previous'],
  ['วันที่', 'Date'],
  ['บันทึก', 'Save'],
  ['แก้ไข', 'Edit'],
  ['เพิ่ม', 'Add'],
  ['ล้าง', 'Clear'],

  ['สัปดาห์ก่อนหน้า', 'Previous Week'],
  ['สัปดาห์ถัดไป', 'Next Week'],
  ['วันก่อนหน้า', 'Previous Day'],
  ['วันถัดไป', 'Next Day'],
  ['สัปดาห์ของวันที่', 'Week of'],
  ['สัปดาห์', 'Week'],
  ['ทุกชั้น', 'All Floors'],
  ['ค้นหาห้อง', 'Search Rooms'],
  ['เช่น 27.03', 'e.g. 27.03'],
  ['ทุกห้อง', 'All Rooms'],
  ['เลือกห้อง', 'Select a Room'],
  ['จองห้อง', 'Book Room'],
  ['จัดการรหัสพิน', 'Manage PIN'],
  ['จัดการ PIN', 'Manage PIN'],
  ['เปลี่ยนรหัสพิน', 'Change PIN'],
  ['รหัสพินใหม่', 'New PIN'],
  ['ยืนยันรหัสพิน', 'Confirm PIN'],
  ['บัญชีของคุณ', 'your account'],
  ['ชื่อผู้ใช้', 'Username'],
  ['กรอกชื่อผู้ใช้', 'Enter your username'],
  ['รหัสผ่าน', 'Password'],
  ['กรอกรหัสผ่าน', 'Enter your password'],
  ['เข้าสู่ระบบ', 'Sign In'],
  ['ออกจากระบบ', 'Sign Out'],
  ['หน้าหลัก', 'Home'],
  ['ตาราง', 'Schedule'],
  ['รหัสพิน', 'PIN'],
  ['ค้นหา', 'Search'],
  ['ห้อง', 'Room'],
  ['เวลา', 'Time'],
  ['สถานะ', 'Status'],
  ['ผู้สอน', 'Instructor'],
  ['ผู้สอน:', 'Instructor:'],
  ['รายวิชา', 'Subject'],
  ['อาคาร', 'Building'],
  ['ชั้น', 'Floor'],
  ['คอมพิวเตอร์', 'Computers'],
  ['ที่นั่ง', 'Seats'],
  ['อุปกรณ์', 'Equipment'],
  ['รูป', 'photos'],
  ['รายการ', 'entries'],
  ['ว่าง', 'Available'],
  ['หมดเวลา', 'Expired'],
  ['ใช้งาน', 'In Use'],
  ['มีตาราง', 'Scheduled'],
  ['กำลังใช้งาน', 'In Use'],
  ['รอเข้าใช้งาน', 'Awaiting Use'],
  ['ยกเลิก', 'Cancelled'],
  ['วันนี้', 'Today'],
  ['ปฏิทิน', 'Calendar'],
  ['เรียลไทม์', 'Real-time'],
  ['พาโนรามา', 'Panorama'],
  ['รายการจอง', 'Bookings'],
  ['วันที่เลือก', 'Selected date'],
  ['ควบคุมเดือนที่แสดง', 'Displayed month controls'],
  ['เดือนก่อนหน้า', 'Previous month'],
  ['เดือนถัดไป', 'Next month'],
  ['เลือกวันที่', 'Choose date'],
  ['เปิดปฏิทินเลือกวันที่', 'Open date picker'],

  ['เปิดหรือปิดเมนูหลัก', 'Toggle main menu'],
  ['ปิดเมนูหลัก', 'Close main menu'],
  ['เมนูหลัก', 'Main menu'],
  ['ไปหน้าหลัก', 'Go to home'],
  ['ปิดหน้าต่างจองห้อง', 'Close booking dialog'],
  ['ปิดหน้าต่างเปลี่ยนรหัสพิน', 'Close PIN dialog'],
  ['ปิดหน้าต่างค้นหา', 'Close search dialog'],
  ['ปิดหน้าต่างยืนยัน', 'Close confirmation dialog'],
  ['ปิดรายละเอียดห้อง', 'Close room details'],
  ['ดูรายละเอียดห้อง', 'View room details'],
  ['ดูภาพใหญ่', 'View large image'],
  ['ปิดหน้าต่างดูรูป', 'Close image viewer'],
  ['ดูรูปก่อนหน้า', 'Previous image'],
  ['ดูรูปถัดไป', 'Next image'],
  ['เลือกรูปที่ต้องการดู', 'Choose an image'],
  ['ไม่สามารถแสดงรูปนี้ได้', 'This image cannot be displayed'],
  ['เปลี่ยนเป็นโหมดสว่าง', 'Switch to light theme'],
  ['เปลี่ยนเป็นโหมดมืด', 'Switch to dark theme'],

  ['วันอาทิตย์', 'Sunday'], ['วันจันทร์', 'Monday'], ['วันอังคาร', 'Tuesday'],
  ['วันพุธ', 'Wednesday'], ['วันพฤหัสบดี', 'Thursday'], ['วันศุกร์', 'Friday'], ['วันเสาร์', 'Saturday'],
  ['อาทิตย์', 'Sunday'], ['จันทร์', 'Monday'], ['อังคาร', 'Tuesday'], ['พุธ', 'Wednesday'],
  ['พฤหัสบดี', 'Thursday'], ['ศุกร์', 'Friday'], ['เสาร์', 'Saturday'],
  ['มกราคม', 'January'], ['กุมภาพันธ์', 'February'], ['มีนาคม', 'March'], ['เมษายน', 'April'],
  ['พฤษภาคม', 'May'], ['มิถุนายน', 'June'], ['กรกฎาคม', 'July'], ['สิงหาคม', 'August'],
  ['กันยายน', 'September'], ['ตุลาคม', 'October'], ['พฤศจิกายน', 'November'], ['ธันวาคม', 'December'],
] as const

const thaiToEnglish = new Map(translations)
const englishToThai = new Map(translations.map(([th, en]) => [en, th]))

const thaiMonths: Record<string, string> = {
  มกราคม: 'January', กุมภาพันธ์: 'February', มีนาคม: 'March', เมษายน: 'April',
  พฤษภาคม: 'May', มิถุนายน: 'June', กรกฎาคม: 'July', สิงหาคม: 'August',
  กันยายน: 'September', ตุลาคม: 'October', พฤศจิกายน: 'November', ธันวาคม: 'December',
}
const thaiShortMonths: Record<string, string> = {
  'ม.ค.': 'Jan', 'ก.พ.': 'Feb', 'มี.ค.': 'Mar', 'เม.ย.': 'Apr', 'พ.ค.': 'May', 'มิ.ย.': 'Jun',
  'ก.ค.': 'Jul', 'ส.ค.': 'Aug', 'ก.ย.': 'Sep', 'ต.ค.': 'Oct', 'พ.ย.': 'Nov', 'ธ.ค.': 'Dec',
}
const thaiWeekdays: Record<string, string> = {
  วันอาทิตย์: 'Sunday', วันจันทร์: 'Monday', วันอังคาร: 'Tuesday', วันพุธ: 'Wednesday',
  วันพฤหัสบดี: 'Thursday', วันศุกร์: 'Friday', วันเสาร์: 'Saturday',
}
const thaiShortWeekdays: Record<string, string> = {
  อาทิตย์: 'Sun', อา: 'Sun', จันทร์: 'Mon', จ: 'Mon', อังคาร: 'Tue', อ: 'Tue',
  พุธ: 'Wed', พ: 'Wed', พฤหัส: 'Thu', พฤ: 'Thu', ศุกร์: 'Fri', ศ: 'Fri', เสาร์: 'Sat', ส: 'Sat',
}
const reverseRecord = (source: Record<string, string>) => Object.fromEntries(Object.entries(source).map(([key, value]) => [value, key]))
const englishMonths = reverseRecord(thaiMonths)
const englishShortMonths = reverseRecord(thaiShortMonths)
const englishWeekdays = reverseRecord(thaiWeekdays)
const englishShortWeekdays: Record<string, string> = { Sun: 'อาทิตย์', Mon: 'จันทร์', Tue: 'อังคาร', Wed: 'พุธ', Thu: 'พฤหัส', Fri: 'ศุกร์', Sat: 'เสาร์' }

function toChristianYear(year: string) {
  const numeric = Number(year)
  return String(numeric > 2400 ? numeric - 543 : numeric)
}

function toBuddhistYear(year: string) {
  const numeric = Number(year)
  return String(numeric < 2400 ? numeric + 543 : numeric)
}

function translateDynamicText(core: string, target: AppLocale): string | null {
  let match: RegExpMatchArray | null

  if (target === 'en') {
    if (core.includes(',')) {
      const parts = core.split(',').map(part => part.trim())
      const translated = parts.map(part => {
        const itemCount = part.match(/^มีรายการ (\d+) รายการ$/)
        if (itemCount) return `${itemCount[1]} ${itemCount[1] === '1' ? 'entry' : 'entries'}`
        return translateUiText(part, 'en')
      })
      if (translated.some((part, index) => part !== parts[index])) return translated.join(', ')
    }

    match = core.match(/^(วัน(?:อาทิตย์|จันทร์|อังคาร|พุธ|พฤหัสบดี|ศุกร์|เสาร์))ที่\s+(\d{1,2})\s+(\S+)\s+(\d{4})$/)
    if (match && thaiWeekdays[match[1]] && thaiMonths[match[3]]) {
      return `${thaiWeekdays[match[1]]}, ${thaiMonths[match[3]]} ${match[2]}, ${toChristianYear(match[4])}`
    }

    match = core.match(/^([ก-๙.]+)\s+(\d{1,2})\s+([ก-๙.]+)\s+(\d{4})(?:\s+(\d+)\s+รายการ)?$/)
    if (match) {
      const weekday = thaiShortWeekdays[match[1].replace(/\.$/, '')]
      const month = thaiShortMonths[match[3]]
      if (weekday && month) return `${weekday}, ${month} ${match[2]}, ${toChristianYear(match[4])}${match[5] ? ` · ${match[5]} entries` : ''}`
    }

    match = core.match(/^(\S+)\s+(\d{4})$/)
    if (match && thaiMonths[match[1]]) return `${thaiMonths[match[1]]} ${toChristianYear(match[2])}`

    const patterns: Array<[RegExp, (...parts: string[]) => string]> = [
      [/^(\d+) ห้อง$/, count => `${count} ${count === '1' ? 'room' : 'rooms'}`],
      [/^(\d+) รายการ$/, count => `${count} ${count === '1' ? 'entry' : 'entries'}`],
      [/^ว่างถึง (.+?) น\.$/, time => `Available until ${time}`],
      [/^ถึง (.+?) น\.$/, time => `Until ${time}`],
      [/^ดูตารางการใช้ห้อง (.+)$/, room => `View schedule for room ${room}`],
      [/^จองห้อง (.+)$/, room => `Book room ${room}`],
      [/^ผู้สอน:\s*(.+)$/, name => `Instructor: ${name}`],
      [/^ตรวจพบ (\d+) คน$/, count => `${count} people detected`],
      [/^ห้อง (.+)$/, room => `Room ${room}`],
      [/^ชั้น (.+)$/, floor => `Floor ${floor}`],
      [/^คาบ (\d+)\s*—\s*(.+)$/, (period, time) => `Period ${period} — ${time}`],
      [/^กำลังแสดงมุมมอง (.+)$/, view => `Currently showing: ${translateUiText(view, 'en')}`],
      [/^วันที่เลือก (.+) มี (\d+) รายการ$/, (date, count) => `Selected date: ${translateUiText(date, 'en')} · ${count} entries`],
      [/^รวมรายการจอง (\d+) รายการ$/, count => `${count} merged bookings`],
      [/^ไม่สามารถโหลดข้อมูลได้:\s*(.+)$/, error => `Unable to load data: ${error}`],
      [/^ไม่สามารถโหลดปฏิทินรวมได้:\s*(.+)$/, error => `Unable to load the full calendar: ${error}`],
      [/^ไม่สามารถลบตารางได้:\s*(.+)$/, error => `Unable to delete the schedule: ${error}`],
      [/^ไม่สามารถยกเลิกได้:\s*(.+)$/, error => `Unable to cancel: ${error}`],
      [/^ปฏิทิน (.+) ทุกห้อง$/, month => `${translateUiText(month, 'en')} calendar · all rooms`],
      [/^ปฏิทิน (.+)$/, month => `${translateUiText(month, 'en')} calendar`],
      [/^ตารางการใช้ห้อง (.+)$/, date => `Room schedule for ${translateUiText(date, 'en')}`],
      [/^รูปที่ (\d+) จาก (\d+)$/, (current, total) => `Image ${current} of ${total}`],
      [/^ภาพห้อง (.+)$/, room => `Room ${room} photo`],
      [/^เปิดดู(.+)ขนาดใหญ่$/, label => `Open ${translateUiText(label, 'en')} in full size`],
      [/^แสดง(.+)$/, label => `Show ${label}`],
      [/^ดูรูปที่เหลืออีก (\d+) รูป$/, count => `View ${count} more photos`],
      [/^ดู(.+)$/, label => `View ${label}`],
    ]
    for (const [pattern, replacer] of patterns) {
      match = core.match(pattern)
      if (match) return replacer(...match.slice(1))
    }
    return null
  }

  match = core.match(/^(Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday),\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})$/)
  if (match) return `${englishWeekdays[match[1]]}ที่ ${match[3]} ${englishMonths[match[2]]} ${toBuddhistYear(match[4])}`

  match = core.match(/^(Sun|Mon|Tue|Wed|Thu|Fri|Sat),\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+(\d{4})(?:\s+·\s+(\d+) entries)?$/)
  if (match) return `${englishShortWeekdays[match[1]]} ${match[3]} ${englishShortMonths[match[2]]} ${toBuddhistYear(match[4])}${match[5] ? ` ${match[5]} รายการ` : ''}`

  match = core.match(/^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})$/)
  if (match) return `${englishMonths[match[1]]} ${toBuddhistYear(match[2])}`

  match = core.match(/^(Sun|Mon|Tue|Wed|Thu|Fri|Sat),\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),\s+(\d{4}),\s+(.+)$/)
  if (match) {
    const date = `${englishShortWeekdays[match[1]]} ${match[3]} ${englishShortMonths[match[2]]} ${toBuddhistYear(match[4])}`
    const suffixes = match[5].split(',').map(part => translateUiText(part.trim(), 'th'))
    return `${date}, ${suffixes.join(', ')}`
  }

  const reversePatterns: Array<[RegExp, (...parts: string[]) => string]> = [
    [/^(\d+) rooms?$/, count => `${count} ห้อง`],
    [/^(\d+) entr(?:y|ies)$/, count => `${count} รายการ`],
    [/^Available until (.+)$/, time => `ว่างถึง ${time} น.`],
    [/^Until (.+)$/, time => `ถึง ${time} น.`],
    [/^View schedule for room (.+)$/, room => `ดูตารางการใช้ห้อง ${room}`],
    [/^Book room (.+)$/, room => `จองห้อง ${room}`],
    [/^Instructor:\s*(.+)$/, name => `ผู้สอน: ${name}`],
    [/^(\d+) people detected$/, count => `ตรวจพบ ${count} คน`],
    [/^Floor (.+)$/, floor => `ชั้น ${floor}`],
    [/^Period (\d+)\s*—\s*(.+)$/, (period, time) => `คาบ ${period} — ${time}`],
    [/^Currently showing:\s*(.+)$/, view => `กำลังแสดงมุมมอง ${translateUiText(view, 'th')}`],
    [/^(\d+) merged bookings$/, count => `รวมรายการจอง ${count} รายการ`],
    [/^Selected date:\s*(.+)\s+·\s+(\d+) entries$/, (date, count) => `วันที่เลือก ${translateUiText(date, 'th')} มี ${count} รายการ`],
    [/^(.+) calendar · all rooms$/, month => `ปฏิทิน ${translateUiText(month, 'th')} ทุกห้อง`],
    [/^(.+) calendar$/, month => `ปฏิทิน ${translateUiText(month, 'th')}`],
    [/^Room schedule for (.+)$/, date => `ตารางการใช้ห้อง ${translateUiText(date, 'th')}`],
    [/^Room (.+)$/, room => `ห้อง ${room}`],
    [/^Image (\d+) of (\d+)$/, (current, total) => `รูปที่ ${current} จาก ${total}`],
  ]
  for (const [pattern, replacer] of reversePatterns) {
    match = core.match(pattern)
    if (match) return replacer(...match.slice(1))
  }

  if (core.includes(',')) {
    const parts = core.split(',').map(part => part.trim())
    const translated = parts.map(part => translateUiText(part, 'th'))
    if (translated.some((part, index) => part !== parts[index])) return translated.join(', ')
  }
  return null
}

export function translateUiText(value: string, target: AppLocale = locale.value): string {
  if (!value.trim()) return value
  const leading = value.match(/^\s*/)?.[0] ?? ''
  const trailing = value.match(/\s*$/)?.[0] ?? ''
  const core = value.trim()
  const exact = target === 'en' ? thaiToEnglish.get(core) : englishToThai.get(core)
  if (exact) return `${leading}${exact}${trailing}`
  const dynamic = translateDynamicText(core, target)
  return dynamic ? `${leading}${dynamic}${trailing}` : value
}

const translatedAttributes = ['aria-label', 'title', 'placeholder', 'alt'] as const
const ignoredTags = new Set(['SCRIPT', 'STYLE', 'CODE', 'PRE'])

function isTranslationDisabled(element: Element | null) {
  return Boolean(element?.closest('[translate="no"]'))
}

function translateElement(root: Node, target: AppLocale) {
  if (root.nodeType === Node.TEXT_NODE) {
    const parent = root.parentElement
    if (!parent || ignoredTags.has(parent.tagName) || isTranslationDisabled(parent)) return
    const next = translateUiText(root.nodeValue ?? '', target)
    if (next !== root.nodeValue) root.nodeValue = next
    return
  }

  if (!(root instanceof Element) && !(root instanceof DocumentFragment) && !(root instanceof Document)) return
  if (root instanceof Element) {
    if (isTranslationDisabled(root)) return
    for (const attribute of translatedAttributes) {
      const value = root.getAttribute(attribute)
      if (value) root.setAttribute(attribute, translateUiText(value, target))
    }
  }

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT)
  let node: Node | null
  while ((node = walker.nextNode())) {
    if (node.nodeType === Node.TEXT_NODE) {
      const parent = node.parentElement
      if (!parent || ignoredTags.has(parent.tagName) || isTranslationDisabled(parent)) continue
      const next = translateUiText(node.nodeValue ?? '', target)
      if (next !== node.nodeValue) node.nodeValue = next
    } else if (node instanceof Element) {
      for (const attribute of translatedAttributes) {
        const value = node.getAttribute(attribute)
        if (value) node.setAttribute(attribute, translateUiText(value, target))
      }
    }
  }
}

let observer: MutationObserver | null = null

function applyDocumentLanguage() {
  document.documentElement.lang = locale.value
  document.documentElement.dir = 'ltr'
  document.title = locale.value === 'th'
    ? 'ระบบบริหารจัดการห้องคอมพิวเตอร์'
    : 'Computer Room Management System'

  observer?.disconnect()
  translateElement(document.body, locale.value)
  observer?.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: [...translatedAttributes] })
}

export function setLocale(next: AppLocale) {
  locale.value = next
  localStorage.setItem(STORAGE_KEY, next)
  applyDocumentLanguage()
}

export function installDocumentI18n() {
  observer?.disconnect()
  observer = new MutationObserver(mutations => {
    observer?.disconnect()
    for (const mutation of mutations) {
      if (mutation.type === 'characterData') translateElement(mutation.target, locale.value)
      if (mutation.type === 'attributes') translateElement(mutation.target, locale.value)
      mutation.addedNodes.forEach(node => translateElement(node, locale.value))
    }
    observer?.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: [...translatedAttributes] })
  })
  applyDocumentLanguage()
}
