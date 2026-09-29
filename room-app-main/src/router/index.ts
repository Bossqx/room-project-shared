import { createRouter, createWebHistory } from "vue-router";

const DisplayView = () => import("../views/DisplayView.vue");
const ConfirmSchedule = () => import("../views/confirmSchedule.vue");
const SelfConfirmSchedule = () => import("../views/SelfConfirm.vue");
const Login = () => import("../views/Login.vue");
const BookingSchedule = () => import("../views/BookingScheduleV1.vue");
const ScheduleDesktopV1 = () => import("../views/ScheduleDesktopV1.vue");
const DisplayEmptyRoomsV1 = () => import("../views/DisplayEmptyRoomV1.vue");
const Booking = () => import("../views/Booking.vue");
const StaffAccess = () => import("../views/StaffAccess.vue");
const StaffSumitClose = () => import("../views/StaffSumitClose.vue");
const SubmitClose = StaffSumitClose;
const UserLayoute = () => import("../layouts/UserLayoute.vue");
const PCLayoute = () => import("../layouts/PCLayoute.vue");
const GeneralLayout = () => import("../layouts/GeneralLayout.vue");
const SetFrameLayout = () => import("../layouts/SetFrameLayout.vue");
const ChangePin = () => import("../views/ChangePin.vue");
const AdminLayout = () => import("../layouts/AdminLayoute.vue");
const AdminMigration = () => import("../views/AdminMigration.vue");
const SemesterManage = () => import("../views/SemesterManage.vue");
const AdminManageSchedule = () => import("../views/AdminManageSchedule.vue");
const Dashboard = () => import("../views/dashboard.vue");
const AdminDashboard = () => import("../views/AdminDashboard.vue");
const ScheduleAll = () => import("../views/ScheduleAll.vue");
const ScheduleDashboard = () => import("../views/ScheduleDashboard.vue");
const ScheduleInfo = () => import("../views/ScheduleInfo.vue");
const InformationMobile = () => import("../views/InformationMobile.vue");
const RoomAdmin = () => import("../views/RoomAdmin.vue");
const AdminCancelRoom = () => import("../views/AdminCancelRoom.vue");
const AproveUsage = () => import("../views/AproveUsage.vue");
const DashboardTestLayout = () => import("../layouts/DashboardTestLayout.vue");
const DashboardTest = () => import("../views/DashboardTest.vue");
const DashboardTest2 = () => import("../views/DashboardTest2.vue");
const DashboardTest3 = () => import("../views/DashboardTest3.vue");
const HomeDashboard = () => import("../views/HomeDashboard.vue");

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(to, _from, savedPosition) {
    // The public dashboard must always open from its header. Mobile Safari
    // otherwise restores the previous page offset after reload/PWA launch.
    if (to.path === "/" || to.path === "/dashboard-first") {
      return { left: 0, top: 0 };
    }
    return savedPosition ?? { left: 0, top: 0 };
  },
  routes: [
    { path: "/qr-front", name: "display", component: DisplayView },
    { path: "/confirm", name: "confirm", component: ConfirmSchedule },
    { path: "/staff-access", name: "staff-access", component: StaffAccess },
    { path: "/login", name: "login", component: Login },
    {
      path: "/staff-close",
      component: SetFrameLayout,
      children: [{ path: "", name: "staff-close", component: StaffSumitClose }],
    },
    {
      path: "/submit-close",
      component: SetFrameLayout,
      children: [{ path: "", name: "submit-close", component: SubmitClose }],
    },
    {
      path: "/",
      component: GeneralLayout,
      children: [
        { path: "", redirect: "/dashboard-first" },
        {
          path: "dashboard-first",
          name: "dashboard-first",
          component: HomeDashboard,
        },
      ],
    },
    {
      path: "/dashboard-test",
      component: DashboardTestLayout,
      children: [
        { path: "", name: "dashboard-test", component: DashboardTest },
      ],
    },
    {
      path: "/dashboard-test2",
      component: DashboardTestLayout,
      children: [
        { path: "", name: "dashboard-test2", component: DashboardTest2 },
      ],
    },
    {
      path: "/dashboard-test3",
      component: DashboardTestLayout,
      children: [
        { path: "", name: "dashboard-test3", component: DashboardTest3 },
      ],
    },
    {
      path: "/dashboard-test4",
      component: DashboardTestLayout,
      children: [
        { path: "", name: "dashboard-test4", component: HomeDashboard },
      ],
    },

    {
      path: "/",
      component: UserLayoute,
      children: [
        { path: "", redirect: "/login" },
        {
          path: "mobile/schedule",
          name: "mobile/schedule",
          component: BookingSchedule,
        },
        {
          path: "mobile/empty-rooms",
          name: "mobile/empty-rooms",
          component: DisplayEmptyRoomsV1,
        },
        { path: "mobile/booking", name: "mobile/booking", component: Booking },
        { path: "mobile/home", name: "mobile/home", component: InformationMobile },
        {
          path: "self-confirm",
          name: "self-confirm",
          component: SelfConfirmSchedule,
        },
        {
          path: "/mobile/change-pin",
          name: "/mobile/change-pin",
          component: ChangePin,
        },
      ],
    },
    {
      path: "/desktop",
      component: PCLayoute,
      children: [
        {
          path: "/desktop/schedule",
          name: "/desktop/schedule",
          component: ScheduleDesktopV1,
        },
        {
          path: "/desktop/home",
          name: "/desktop/home",
          component: ScheduleAll,
        },
        {
          path: "/desktop/room-summary",
          name: "/desktop/room-summary",
          component: ScheduleDashboard,
        },
        {
          path: "/desktop/schedule-info",
          name: "/desktop/schedule-info",
          component: ScheduleInfo,
        },
        {
          path: "/desktop/overview",
          name: "/desktop/overview",
          component: HomeDashboard,
        },
      ],
    },

    {
      path: "/admin",
      component: AdminLayout,
      children: [
        {
          path: "/admin/dashboard-new",
          name: "/admin/dashboard-new",
          component: AdminDashboard,
        },
        { path: "/admin/home", name: "/admin/home", component: AdminMigration },
        {
          path: "/admin/semester",
          name: "/admin/semester",
          component: SemesterManage,
        },
        {
          path: "/admin/schedule",
          name: "/admin/schedule",
          component: AdminManageSchedule,
        },
        {
          path: "/admin/rooms",
          name: "/admin/rooms",
          component: RoomAdmin,
        },
        {
          path: "/admin/cancel-room",
          name: "/admin/cancel-room",
          component: AdminCancelRoom,
        },
        {
          path: "/admin/approve-usage",
          name: "/admin/approve-usage",
          component: AproveUsage,
        },
      ],
    },
    {
      path: "/dashboard",
      component: AdminLayout,
      children: [
        { path: "/dashboard", name: "/dashboard", component: Dashboard },
      ],
    },
  ],
});

export default router;
