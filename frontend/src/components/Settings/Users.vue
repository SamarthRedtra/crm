<template>
  <div class="flex h-full flex-col gap-6 p-6 text-ink-gray-8">
    <!-- Header -->
    <div class="flex justify-between px-2 pt-2">
      <div class="flex flex-col gap-1 w-9/12">
        <h2 class="flex gap-2 text-xl font-semibold leading-none h-5">
          {{ __('Users') }}
        </h2>
        <p class="text-p-base text-ink-gray-6">
          {{
            __(
              'Manage CRM users by adding or inviting them, and assign roles to control their access and permissions',
            )
          }}
        </p>
      </div>
      <div class="flex item-center space-x-2 w-3/12 justify-end">
        <Button
          v-if="canInviteTeam"
          :label="__('Invite team members')"
          icon-left="user-plus"
          @click="activeSettingsPage = 'Invite team'"
        />
        <Dropdown
          :options="newUserOptions"
          :button="{
            label: __('New'),
            iconLeft: 'plus',
            variant: 'solid',
          }"
          placement="right"
        />
      </div>
    </div>

    <!-- loading state -->
    <div v-if="users.loading" class="flex mt-28 justify-between w-full h-full">
      <Button
        :loading="users.loading"
        variant="ghost"
        class="w-full"
        size="2xl"
      />
    </div>

    <!-- Empty State -->
    <div
      v-else-if="!hasRows"
      class="flex justify-between w-full h-full"
    >
      <div
        class="text-ink-gray-4 border border-dashed rounded w-full flex items-center justify-center min-h-[12rem]"
      >
        {{ __('No users found') }}
      </div>
    </div>

    <!-- Users List -->
    <div v-else class="flex flex-col overflow-hidden">
      <div
        v-if="crmUsersPool.length > 10"
        class="flex items-center justify-between mb-4 px-2 pt-0.5"
      >
        <TextInput
          ref="searchRef"
          v-model="search"
          :placeholder="__('Search user')"
          class="w-1/3"
          :debounce="300"
        >
          <template #prefix>
            <FeatherIcon name="search" class="h-4 w-4 text-ink-gray-6" />
          </template>
        </TextInput>
        <FormControl
          type="select"
          v-model="currentRole"
          :options="roleFilterOptions"
        />
      </div>
      <ul class="divide-y divide-outline-gray-modals overflow-y-auto px-2">
        <template v-for="user in usersList" :key="user.name">
          <li class="flex items-center justify-between py-2">
            <div class="flex items-center">
              <Avatar
                :image="user.user_image"
                :label="user.full_name"
                size="xl"
              />
              <div class="flex flex-col ml-3">
                <div class="flex items-center text-p-base text-ink-gray-8">
                  {{ user.full_name }}
                </div>
                <div class="text-p-sm text-ink-gray-5">
                  {{ user.name }}
                </div>
              </div>
            </div>
            <div class="flex flex-wrap gap-2 items-center justify-end">
              <Dropdown
                v-if="showAgencyRoleControl(user)"
                :options="getAgencyRoleOptions(user)"
                :button="{
                  label: agencyRoleLabel(user.agency_role),
                  iconRight: 'chevron-down',
                  iconLeft: 'users',
                }"
                placement="right"
              />
              <Dropdown
                :options="getMoreOptions(user)"
                :button="{
                  icon: 'more-horizontal',
                  onblur: (e) => {
                    e.stopPropagation()
                    confirmRemove = false
                  },
                }"
                placement="right"
              />
              <Tooltip
                v-if="usersScopeAll && isManager() && user.role == 'System Manager'"
                :text="__('Cannot change role of user with Admin access')"
              >
                <Button :label="__('Admin')" icon-left="shield" />
              </Tooltip>
              <Dropdown
                v-else-if="usersScopeAll && showCrmRoleControl(user)"
                :options="getDropdownOptions(user)"
                :button="{
                  label: roleMap[user.role] || user.role,
                  iconRight: 'chevron-down',
                  iconLeft:
                    user.role === 'System Manager'
                      ? 'shield'
                      : user.role === 'Sales Manager'
                        ? 'briefcase'
                        : 'user-check',
                }"
                placement="right"
              />
            </div>
          </li>
        </template>
        <!-- Load More Button -->
        <div
          v-if="!users.loading && users.hasNextPage"
          class="flex justify-center"
        >
          <Button
            class="mt-3.5 p-2"
            @click="() => users.next()"
            :loading="users.loading"
            :label="__('Load More')"
            icon-left="refresh-cw"
          />
        </div>
      </ul>
    </div>
  </div>
  <AddExistingUserModal
    v-if="showAddExistingModal"
    v-model="showAddExistingModal"
  />
</template>

<script setup>
import AddExistingUserModal from '@/components/Modals/AddExistingUserModal.vue'
import { activeSettingsPage } from '@/composables/settings'
import { sessionStore } from '@/stores/session'
import { agencyStore } from '@/stores/agency'
import { usersStore } from '@/stores/users'
import { DropdownOption } from '@/utils'
import {
  Dropdown,
  Avatar,
  TextInput,
  toast,
  call,
  FeatherIcon,
  Tooltip,
  FormControl,
  Button,
} from 'frappe-ui'
import { storeToRefs } from 'pinia'
import { ref, computed, onMounted } from 'vue'

const session = sessionStore()
const { user: sessionUserId } = storeToRefs(session)
const { users, isAdmin, isManager, getUser } = usersStore()
const agency = agencyStore()

const showAddExistingModal = ref(false)
const searchRef = ref(null)
const search = ref('')
const currentRole = ref('All')

const usersScopeAll = computed(
  () => users.data?.viewerMeta?.users_scope === 'all',
)

const canInviteTeam = computed(() =>
  Boolean(agency.context?.can_manage_team) &&
  (isManager() || getUser().role === 'Agency Admin'),
)

const newUserOptions = computed(() => {
  const options = [
    {
      label: __('Add Existing User'),
      onClick: () => (showAddExistingModal.value = true),
    },
  ]
  if (canInviteTeam.value) {
    options.push({
      label: __('Invite team'),
      onClick: () => (activeSettingsPage.value = 'Invite team'),
    })
  }
  return options
})

const crmUsersPool = computed(() => {
  const raw =
    users.data?.crmUsers?.filter((user) => user.name !== 'Administrator') || []
  return raw
})

const hasRows = computed(() => crmUsersPool.value.length > 0)

const roleFilterOptions = computed(() => {
  if (!usersScopeAll.value) {
    return [
      { label: __('All'), value: 'All' },
      { label: __('Admin'), value: 'Admin' },
      { label: __('Manager'), value: 'Manager' },
      { label: __('Agent'), value: 'Agent' },
    ]
  }
  return [
    { label: __('All'), value: 'All' },
    { label: __('CRM Admin'), value: 'System Manager' },
    { label: __('CRM Manager'), value: 'Sales Manager' },
    { label: __('Agency Admin'), value: 'Agency Admin' },
    { label: __('Agency Manager'), value: 'Agency Manager' },
    { label: __('Sales User'), value: 'Sales User' },
  ]
})

const roleMap = {
  'System Manager': __('CRM Admin'),
  'Sales Manager': __('CRM Manager'),
  'Agency Admin': __('Agency Admin'),
  'Agency Manager': __('Agency Manager'),
  'Sales User': __('Sales User'),
}

const agencyRoleLabels = {
  Admin: __('Admin'),
  Manager: __('Manager'),
  Agent: __('Agent'),
}

function agencyRoleLabel(role) {
  if (!role) return __('Agency role')
  return agencyRoleLabels[role] || role
}

const canEditAgencyTeamRole = computed(() => {
  if (sessionUserId.value === 'Administrator') return true
  const role = getUser().role
  return (
    role === 'System Manager' ||
    role === 'Sales Manager' ||
    role === 'Agency Admin' ||
    role === 'Agency Manager'
  )
})

function showAgencyRoleControl(user) {
  return Boolean(user.agent_agency) && canEditAgencyTeamRole.value
}

function showCrmRoleControl(_user) {
  if (!usersScopeAll.value) return false
  if (sessionUserId.value !== 'Administrator' && !isAdmin() && !isManager()) {
    return false
  }
  return true
}

const usersList = computed(() => {
  let filteredUsers = [...crmUsersPool.value]

  return filteredUsers
    .filter(
      (user) =>
        user.name?.includes(search.value) ||
        user.full_name?.includes(search.value),
    )
    .filter((user) => {
      if (currentRole.value === 'All') return true
      if (!usersScopeAll.value) {
        return user.agency_role === currentRole.value
      }
      return user.role === currentRole.value
    })
})

const confirmRemove = ref(false)

function getMoreOptions(user) {
  let options = [
    {
      label: __('Remove'),
      icon: 'trash-2',
      onClick: (e) => {
        e.preventDefault()
        e.stopPropagation()
        confirmRemove.value = true
      },
      condition: () => !confirmRemove.value,
    },
    {
      label: __('Confirm Remove'),
      icon: 'trash-2',
      theme: 'red',
      onClick: () => removeUser(user, true),
      condition: () => confirmRemove.value,
    },
  ]

  return options.filter((option) => option.condition?.() || true)
}

function getAgencyRoleOptions(user) {
  const opts = ['Agent', 'Manager', 'Admin'].map((role) => ({
    label: agencyRoleLabels[role],
    component: () =>
      DropdownOption({
        option: agencyRoleLabels[role],
        icon: 'users',
        selected: user.agency_role === role,
      }),
    onClick: () => updateAgencyRole(user, role),
  }))
  return opts
}

function updateAgencyRole(user, newRole) {
  if (user.agency_role === newRole) return

  call('crm.api.user.update_agency_team_member_role', {
    user: user.name,
    agency_role: newRole,
  }).then(() => {
    toast.success(
      __('{0} is now {1}', [
        user.full_name,
        agencyRoleLabels[newRole] || newRole,
      ]),
    )
    users.reload()
  })
}

function getDropdownOptions(user) {
  let options = [
    {
      label: __('CRM Admin'),
      component: () =>
        DropdownOption({
          option: __('CRM Admin'),
          icon: 'shield',
          selected: user.role === 'System Manager',
        }),
      onClick: () => updateRole(user, 'System Manager'),
      condition: () => isAdmin(),
    },
    {
      label: __('CRM Manager'),
      component: () =>
        DropdownOption({
          option: __('CRM Manager'),
          icon: 'briefcase',
          selected: user.role === 'Sales Manager',
        }),
      onClick: () => updateRole(user, 'Sales Manager'),
      condition: () => isManager(),
    },
    {
      label: __('Agency Admin'),
      component: () =>
        DropdownOption({
          option: __('Agency Admin'),
          icon: 'shield',
          selected: user.role === 'Agency Admin',
        }),
      onClick: () => updateRole(user, 'Agency Admin'),
      condition: () => isManager(),
    },
    {
      label: __('Agency Manager'),
      component: () =>
        DropdownOption({
          option: __('Agency Manager'),
          icon: 'briefcase',
          selected: user.role === 'Agency Manager',
        }),
      onClick: () => updateRole(user, 'Agency Manager'),
      condition: () => isManager(),
    },
    {
      label: __('Sales User'),
      component: () =>
        DropdownOption({
          option: __('Sales User'),
          icon: 'user-check',
          selected: user.role === 'Sales User',
        }),
      onClick: () => updateRole(user, 'Sales User'),
    },
  ]

  return options.filter((option) => option.condition?.() || true)
}

function updateRole(user, newRole) {
  if (user.role === newRole) return

  call('crm.api.user.update_user_role', {
    user: user.name,
    new_role: newRole,
  }).then(() => {
    toast.success(
      __('{0} has been granted {1} access', [user.full_name, roleMap[newRole]]),
    )
    users.reload()
  })
}

function removeUser(user) {
  call('crm.api.user.remove_user', {
    user: user.name,
  }).then(() => {
    toast.success(__('User {0} has been removed', [user.full_name]))
    users.reload()
  })
}

onMounted(() => {
  if (searchRef.value) {
    searchRef.value.el.focus()
  }
})
</script>
